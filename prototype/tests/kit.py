"""시나리오 공용 도구. 출력은 짧게(TPM 8K 대비)."""
import shutil, json, requests, unicodedata
from pathlib import Path
ROOT=Path("/workspace/test_downloads"); MOVES=[]; APPROVER=[lambda s,d:("approve",d)]
def reset(names):
    shutil.rmtree(ROOT,ignore_errors=True); ROOT.mkdir(parents=True); MOVES.clear()
    for n in names: (ROOT/n).write_text("dummy "+n)
def tree(): return sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file())
def list_files() -> str:
    """List files (relative paths) in the downloads copy folder."""
    return "\n".join(tree())
def read_file(path: str) -> str:
    """Read first 100 chars of a file in the folder."""
    p=ROOT/unicodedata.normalize("NFC",path)
    if not p.exists():
        p=ROOT/unicodedata.normalize("NFD",path)
    return p.read_text(errors="ignore")[:100] if p.exists() else f"error: '{path}' not found. Call list_files."
def apply_move(src: str, dst: str) -> str:
    """Move/rename one file inside the folder (dst relative, e.g. 'Images/a.png'). A human approves, rejects or edits each move. Never deletes."""
    s=ROOT/src
    if not s.exists():
        s=ROOT/unicodedata.normalize("NFD",src)
        if not s.exists(): return f"error: source '{src}' not found. Call list_files."
    d=(ROOT/dst).resolve()
    if ROOT.resolve() not in d.parents: return "error: dst must stay inside the folder"
    verdict,newdst=APPROVER[0](src,dst); print(f"  [승인] {src} -> {dst} : {verdict} {newdst if verdict=='edit' else ''}",flush=True)
    if verdict=="reject": return "REJECTED by human: leave this file where it is. Do not retry."
    d=(ROOT/newdst).resolve(); d.parent.mkdir(parents=True,exist_ok=True); shutil.move(s,d); MOVES.append((src,newdst))
    return f"moved to {newdst}" + (" (human EDITED the destination; follow this pattern)" if verdict=="edit" else "")
B="https://collectionapi.metmuseum.org/public/collection/v1"
def met_search(q: str) -> str:
    """Search Met Museum open-access artworks by English keyword. Returns up to 2 public-domain works or a 'no results' message."""
    try:
        ids=(requests.get(B+".1/search",params={"q":q,"hasImages":"true","limit":20},headers={"User-Agent":"agent-kit-workshop-test/0.1"},timeout=20).json().get("objectIDs") or [])[:8]
        out=[]
        for i in ids:
            o=requests.get(f"{B}/objects/{i}",headers={"User-Agent":"agent-kit-workshop-test/0.1"},timeout=20).json()
            if o.get("isPublicDomain"): out.append({k:o.get(k) for k in("objectID","title","artistDisplayName","objectDate","primaryImageSmall","objectURL")})
            if len(out)==2: break
        return json.dumps(out,ensure_ascii=False) if out else f"no results for '{q}'. Try a different simpler English word."
    except Exception as e: return f"error: {e}"

# ---- .env 읽기 (학생마다 자기 키) ----
import os, re
def load_env():
    for p in [Path(__file__).parent/".env", Path(__file__).parent.parent/".env", Path(__file__).parent.parent/".tavily.env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k,v=line.split("=",1); os.environ.setdefault(k.strip(), v.strip().strip('"'))
load_env()
def redact(s):
    s=str(s)
    for k in ("TAVILY_API_KEY","ZAI_API_KEY"):
        v=os.environ.get(k)
        if v: s=s.replace(v,"***")
    return re.sub(r"tavilyApiKey=[^&\s'\"]+","tavilyApiKey=***",s)

# ---- Tavily 원격 MCP (streamable HTTP) + 호출 횟수 제한 ----
WEB_CAP=int(os.getenv("WEB_CAP","5")); WEB_CALLS=[]; _MC=[None]
def _tavily():
    if _MC[0] is None:
        from aisuite.mcp import MCPClient
        _MC[0]=MCPClient(server_url="https://mcp.tavily.com/mcp/?tavilyApiKey="+os.environ["TAVILY_API_KEY"], name="tavily")
        _MC[0]._t={t.__name__:t for t in _MC[0].get_callable_tools()}
    return _MC[0]._t
def _call(name, **kw):
    if len(WEB_CALLS)>=WEB_CAP: return f"error: web limit reached ({WEB_CAP} calls this run). Stop searching and answer with what you have."
    WEB_CALLS.append((name,kw)); print(f"  [web {len(WEB_CALLS)}/{WEB_CAP}] {name} {kw}",flush=True)
    try: return redact(str(_tavily()[name](**kw))[:4000])
    except Exception as e: return "error: "+redact(e)[:300]
def web_search(query: str) -> str:
    """Search the web. query must be a non-empty search phrase. Returns top 3 results (title, url, snippet)."""
    if not query or not query.strip(): return "error: query is empty. Call again with a search phrase like 'Van Gogh Sunflowers'."
    return _call("tavily_search", query=query, max_results=3)
def web_read(url: str) -> str:
    """Read the main text of one web page by URL (e.g. a Wikipedia article)."""
    if not url or not url.startswith("http"): return "error: give a full URL starting with http."
    return _call("tavily_extract", urls=[url])
def close_web():
    if _MC[0]: _MC[0].close(); _MC[0]=None

# ---- 갤러리: 모델은 내용만, HTML은 코드가 ----
import html as _h
def write_gallery(met_object_id: int, commentary: str) -> str:
    """Save the exhibition page. Give the Met objectID you chose (from met_search objectURL, e.g. 360837) and a 3-sentence Korean commentary (plain text). Title/artist/date/image are filled in by code from the Met."""
    try:
        r=None
        for v in ("v1.1","v1"):
            r=requests.get(f"https://collectionapi.metmuseum.org/public/collection/{v}/objects/{int(met_object_id)}",headers={"User-Agent":"agent-kit-workshop-test/0.1"},timeout=20)
            if r.status_code==200: break
        if r.status_code!=200: return f"error: Met object {met_object_id} not found ({r.status_code}). Use an objectID from met_search."
        o=r.json()
    except Exception as ex: return f"error: Met API failed ({ex})"
    if not o.get("isPublicDomain"): return f"error: object {met_object_id} is not public domain. Pick another from met_search."
    if not o.get("primaryImageSmall"): return f"error: object {met_object_id} has no image. Pick another from met_search."
    title,artist,date,image_url,met_url=o.get("title"),o.get("artistDisplayName") or "작가 미상",o.get("objectDate"),o["primaryImageSmall"],o.get("objectURL")
    e=lambda x:_h.escape(str(x or ""))
    files="".join(f"<li>{e(f)}</li>" for f in tree())
    page=f"""<!doctype html><html lang="ko"><meta charset="utf-8"><title>내 다운로드 폴더 전시회</title>
<style>body{{font-family:-apple-system,'Pretendard',sans-serif;margin:0;background:#f4f1ea;color:#222}}
header{{padding:48px 8vw 16px}}h1{{font-size:40px;margin:0}}.sub{{color:#777}}
main{{display:grid;grid-template-columns:minmax(260px,1fr) 1fr;gap:40px;padding:24px 8vw 64px}}
figure{{margin:0;background:#fff;padding:20px;box-shadow:0 10px 30px #0002}}img{{width:100%;display:block}}
figcaption{{margin-top:12px;font-size:14px;color:#555}}.card{{background:#fff;padding:24px;line-height:1.7}}
ul{{columns:2;font-size:13px;color:#555}}a{{color:#8a5a00}}</style>
<header><h1>내 다운로드 폴더 전시회</h1><p class="sub">도슨트 에이전트가 고른 오늘의 작품</p></header>
<main><figure><img src="{e(image_url)}" alt="{e(title)}"><figcaption><b>{e(title)}</b><br>{e(artist)} · {e(date)}<br><a href="{e(met_url)}">메트로폴리탄 미술관에서 보기</a></figcaption></figure>
<section><div class="card"><h2>도슨트 해설</h2><p>{e(commentary)}</p></div><h3>이번 전시의 소장품 (정리된 파일)</h3><ul>{files}</ul></section></main></html>"""
    p=Path("/workspace/workshop/tests/out/gallery.html"); p.parent.mkdir(exist_ok=True); p.write_text(page)
    return f"saved {p}: {title} / {artist} / {date}"
