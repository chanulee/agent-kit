"""시험 2: 파일 정리 (가짜 파일 10개를 만들어 실제로 옮김).

- 임시 폴더 안에서만 동작합니다. 내 진짜 파일은 건드리지 않습니다.
- 삭제 도구는 없습니다.
- 승인은 자동 승인으로 대신합니다(시험용).
- 도구는 실패해도 오류를 던지지 않고 "error: ..." 글을 돌려줍니다.
"""
import shutil
import tempfile
from pathlib import Path

from common import run

ROOT = Path(tempfile.mkdtemp(prefix="agentkit_test_downloads_")).resolve()
for n in ["IMG_2031.jpg", "Screenshot 2026-10-01 at 3.12.44 PM.png", "과제3_최종_진짜최종.pdf",
          "invoice_oct.pdf", "resume(1).docx", "font-Pretendard.zip", "moodboard_ref_blue.png",
          "lecture5_notes.txt", "setup.dmg", "receipt_coupang.pdf"]:
    (ROOT / n).write_text("dummy " + n, encoding="utf-8")
LOG = []


def approve(src, dst):
    print(f"  [승인요청] {src} -> {dst} : 자동승인")
    return True


def list_files() -> str:
    """List all files (relative paths) in the downloads copy folder."""
    try:
        return "\n".join(str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file())
    except Exception as e:
        return f"error: {e}"


def read_file(path: str) -> str:
    """Read the first 200 characters of a file in the folder."""
    try:
        p = (ROOT / path).resolve()
        if ROOT not in p.parents:
            return "error: outside the copy folder"
        return p.read_text(errors="ignore")[:200] if p.exists() else "error: not found (call list_files again)"
    except Exception as e:
        return f"error: {e}"


def apply_move(src: str, dst: str) -> str:
    """Move/rename a file inside the folder. dst is a relative path like 'Images/a.png'. Requires human approval. Never deletes."""
    try:
        s, d = (ROOT / src).resolve(), (ROOT / dst).resolve()
        if ROOT not in d.parents or ROOT not in s.parents or not s.exists():
            return "error: invalid path"
        if d.exists():
            return "error: target exists (choose another name)"
        if not approve(src, dst):
            return "denied by user"
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(s), str(d))
        LOG.append((src, dst))
        return "moved"
    except Exception as e:
        return f"error: {e}"


ans, calls, dt = run(
    [{"role": "user", "content": "내 다운로드 폴더를 정리해줘. 먼저 목록을 보고 카테고리 폴더 계획을 세운 뒤, "
                                 "apply_move로 실제로 옮겨줘. 끝나면 한국어로 요약."}],
    [list_files, read_file, apply_move],
    max_turns=15,
)
print("calls", len(calls), [c[0] for c in calls])
print(f"{dt:.1f}s\n", ans)
print("실제 결과:")
print(list_files())
print("moves", len(LOG))
print("시험 폴더:", ROOT, "(직접 확인 후 지워도 됩니다)")
