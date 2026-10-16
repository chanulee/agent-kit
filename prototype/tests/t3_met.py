"""시험 3: 메트로폴리탄 미술관 API에서 공공 도메인 작품 찾기.

키가 필요 없습니다. 검색은 v1.1 주소를 씁니다(옛 /v1/search는 2026-10-01 종료 안내를 돌려줌).
시험 당시에는 옛 주소로 돌렸습니다. v1.1로 고친 뒤 도구 부분(API 호출)은 직접 확인했고, LLM까지 포함한 전체 실행은 아직 못 했습니다. [확인 필요]
"""
import requests

from common import run

BASE = "https://collectionapi.metmuseum.org/public/collection"
HEADERS = {"User-Agent": "agent-kit-workshop-test/0.1"}


def met_search(q: str) -> str:
    """Search the Metropolitan Museum open-access collection. Returns up to 3 public-domain artworks (title, artist, date, medium, image url)."""
    try:
        r = requests.get(f"{BASE}/v1.1/search", params={"q": q, "hasImages": "true", "limit": 20},
                         headers=HEADERS, timeout=20)
        ids = (r.json().get("objectIDs") or [])[:10]
        out = []
        for i in ids:
            o = requests.get(f"{BASE}/v1/objects/{i}", headers=HEADERS, timeout=20).json()
            if o.get("isPublicDomain") and o.get("primaryImageSmall"):
                out.append({k: o.get(k) for k in ("title", "artistDisplayName", "objectDate", "medium",
                                                  "primaryImageSmall", "objectURL")})
            if len(out) == 3:
                break
        return str(out) if out else "error: no public-domain results (try another keyword)"
    except Exception as e:
        return f"error: Met API failed ({e})"


ans, calls, dt = run(
    [{"role": "user", "content": "메트로폴리탄 미술관에서 해바라기 그림을 찾아서 하나 추천하고 이유를 한국어 2문장으로."}],
    [met_search],
)
print(calls, f"{dt:.1f}s\n", ans)
