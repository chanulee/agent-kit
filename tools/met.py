"""미술관 API 도구: 메트로폴리탄 미술관 공개 API(키 필요 없음) + 갤러리 페이지 만들기.

- 검색은 v1.1 주소만 씁니다(옛 /v1/search 는 2026-10-01 종료).
- 후보는 공공 도메인 + 이미지 있음 + 작가가 서로 다른 것 최대 4점.
- 갤러리 HTML은 코드가 만들고, 모델은 작품 번호·이유·해설·출처만 줍니다.
- 출처는 이번 실행에서 웹 도구가 실제로 받은 주소만 남깁니다(지어낸 링크 방지).
"""
import html
import json
from pathlib import Path

import httpx

from tools import folder, tool
from tools.files import all_files

BASE = "https://collectionapi.metmuseum.org/public/collection"
UA = {"User-Agent": "agent-kit-workshop/0.1"}


def _get(url, **params):
    with httpx.Client(headers=UA, timeout=20, follow_redirects=True) as c:
        r = c.get(url, params=params)
        r.raise_for_status()
        return r.json()


@tool("🖼️", group="미술관 API")
def met_search(query: str) -> str:
    """Search The Met open-access collection with a short ENGLISH keyword. Returns up to 4 public-domain candidates
    by different artists (objectID, title, artist, date, medium). Compare them and pick one.

    Args:
        query: 1-3 English words, e.g. 'sunflowers'
    """
    ids = (_get(f"{BASE}/v1.1/search", q=query, hasImages="true", limit=40).get("objectIDs") or [])[:16]
    out, artists = [], set()
    for i in ids:
        try:
            o = _get(f"{BASE}/v1/objects/{i}")
        except Exception:  # noqa: BLE001 - 작품 하나 실패는 건너뜀
            continue
        a = o.get("artistDisplayName") or "?"
        if o.get("isPublicDomain") and o.get("primaryImageSmall") and a not in artists:
            artists.add(a)
            out.append({k: o.get(k) for k in ("objectID", "title", "artistDisplayName", "objectDate", "medium")})
        if len(out) == 4:
            break
    return json.dumps(out, ensure_ascii=False) if out else f"error: '{query}'로 찾은 작품이 없습니다. 더 쉬운 영어 단어로 다시 찾아보세요."


@tool("🏛️", group="미술관 API")
def write_gallery(met_object_id: int, reason: str, commentary: str, sources: list[str]) -> str:
    """Save the exhibition page (gallery.html). Title/artist/date/image are filled in by code from The Met.

    Args:
        met_object_id: objectID chosen from met_search
        reason: one Korean line: why this work fits the folder (vs the other candidates)
        commentary: 3 Korean sentences, plain text
        sources: page URLs you actually got from web_search/web_read this run
    """
    from tools.web import SEEN_URLS
    o = _get(f"{BASE}/v1/objects/{int(met_object_id)}")
    if not (o.get("isPublicDomain") and o.get("primaryImageSmall")):
        return "error: 공공 도메인이 아니거나 이미지가 없는 작품입니다. met_search 후보에서 다시 고르세요."
    norm = lambda u: str(u).strip().rstrip("/")  # noqa: E731
    seen = {norm(u) for u in SEEN_URLS}
    kept = [u for u in dict.fromkeys(sources or []) if norm(u) in seen]
    e = lambda x: html.escape(str(x or ""))  # noqa: E731
    root = folder()
    files = "".join(f"<li>{e(p.relative_to(root).as_posix())}</li>" for p in all_files())
    src = "".join(f'<li><a href="{e(u)}">{e(u)}</a></li>' for u in kept)
    template = (Path(__file__).parent / "gallery_template.html").read_text(encoding="utf-8")
    page = (template.replace("{{image}}", e(o["primaryImageSmall"])).replace("{{title}}", e(o.get("title")))
            .replace("{{artist}}", e(o.get("artistDisplayName") or "작가 미상")).replace("{{date}}", e(o.get("objectDate")))
            .replace("{{met_url}}", e(o.get("objectURL"))).replace("{{reason}}", e(reason))
            .replace("{{commentary}}", e(commentary)).replace("{{sources}}", src).replace("{{files}}", files))
    (root / "gallery.html").write_text(page, encoding="utf-8")
    dropped = [u for u in sources or [] if u not in kept]
    return f"gallery.html 저장: {o.get('title')} / {o.get('artistDisplayName')}. 출처 {len(kept)}개 사용" + \
        (f", 이번에 보지 않은 주소 {len(dropped)}개는 뺐습니다." if dropped else ".")
