import os, shutil
from pathlib import Path
from common import run
ROOT=Path("/workspace/test_downloads"); shutil.rmtree(ROOT,ignore_errors=True); ROOT.mkdir()
for n in ["IMG_2031.jpg","Screenshot 2026-10-01 at 3.12.44 PM.png","과제3_최종_진짜최종.pdf","invoice_oct.pdf","resume(1).docx","font-Pretendard.zip","moodboard_ref_blue.png","lecture5_notes.txt","setup.dmg","receipt_coupang.pdf"]:
    (ROOT/n).write_text("dummy "+n)
LOG=[]
def approve(src,dst): print(f"  [승인요청] {src} -> {dst} : 자동승인"); return True
def list_files() -> str:
    """List all files (relative paths) in the downloads copy folder."""
    return "\n".join(str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file())
def read_file(path: str) -> str:
    """Read the first 200 characters of a file in the folder."""
    p=ROOT/path
    return p.read_text(errors="ignore")[:200] if p.exists() else "error: not found (call list_files again)"
def apply_move(src: str, dst: str) -> str:
    """Move/rename a file inside the folder. dst is a relative path like 'Images/a.png'. Requires human approval. Never deletes."""
    s,d=(ROOT/src).resolve(),(ROOT/dst).resolve()
    if ROOT not in d.parents or not s.exists(): return "error: invalid path"
    if not approve(src,dst): return "denied by user"
    d.parent.mkdir(parents=True,exist_ok=True); shutil.move(s,d); LOG.append((src,dst)); return "moved"
ans,calls,dt=run([{"role":"user","content":"내 다운로드 폴더를 정리해줘. 먼저 목록을 보고 카테고리 폴더 계획을 세운 뒤, apply_move로 실제로 옮겨줘. 끝나면 한국어로 요약."}],[list_files,read_file,apply_move],max_turns=15)
print("calls",len(calls),[c[0] for c in calls]); print(f"{dt:.1f}s\n",ans)
print("실제 결과:"); print(list_files()); print("moves",len(LOG))
