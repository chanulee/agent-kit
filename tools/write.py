"""파일 쓰기 도구: 실습 폴더 안에 마크다운 노트만 새로 만듭니다. 지우거나 덮어쓰지 않습니다."""
from tools import folder, nfc, safe_name, tool


def _new_md(rel: str):
    """만들 .md 경로. 실습 폴더 밖, 덮어쓰기, 마크다운이 아닌 파일은 거절합니다."""
    root = folder().resolve()
    rel = nfc(str(rel).strip().replace("\\", "/"))
    while rel.startswith("./"):
        rel = rel[2:]
    if not rel or rel.startswith(("/", "~")) or ".." in rel.split("/") or ":" in rel.split("/")[0]:
        raise PermissionError(f"실습 폴더 밖 경로는 쓸 수 없습니다: {rel}")
    if not rel.lower().endswith(".md"):
        raise PermissionError("마크다운(.md) 파일만 만들 수 있습니다.")
    if rel.startswith(".agentkit") or "/.agentkit" in rel:
        raise PermissionError("내부 폴더에는 쓸 수 없습니다.")
    rel = "/".join(safe_name(p) for p in rel.split("/") if p not in ("", "."))  # Windows에서 못 쓰는 글자 정리
    dest = (root / rel).resolve()
    if root not in dest.parents:
        raise PermissionError("실습 폴더 밖 경로는 쓸 수 없습니다.")
    return dest


@tool("✍️", group="파일 쓰기")
def write_file(path: str, content: str) -> str:
    """Create a new markdown file inside the practice folder. Refuses to overwrite or leave the folder.

    Args:
        path: relative path ending in .md, e.g. '리서치/노트.md'
        content: full markdown text to write
    """
    text = str(content or "")
    if not text.strip():
        return "error: 내용이 비어 있습니다. 요약, 핵심, 출처를 적어 주세요."
    if len(text) > 30000:
        return "error: 내용이 너무 깁니다. 30,000자 안으로 줄여 주세요."
    try:
        dest = _new_md(path)
    except (PermissionError, FileNotFoundError) as e:
        return f"error: {e}"
    if dest.exists():
        return f"error: 이미 있는 파일입니다 ({dest.name}). 다른 이름을 쓰세요. 덮어쓰지 않습니다."
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    rel = nfc(dest.relative_to(folder().resolve()).as_posix())
    return f"저장했습니다: {rel} ({len(text)}자). 지우는 기능은 없습니다."
