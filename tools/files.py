"""파일 보기 도구: 실습 폴더 안에서만, 읽기만 합니다. 엿보기는 앞 500자, 이미지는 크기만."""
from collections import Counter
from datetime import datetime

from tools import find, folder, nfc, tool

SKIP = {".agentkit", ".DS_Store", "gallery.html", "_dates.json"}
KINDS = {"이미지": ".png .jpg .jpeg .gif .webp .heic", "문서": ".pdf .doc .docx .hwp .txt .md .ppt .pptx .key",
         "표": ".xls .xlsx .csv", "압축": ".zip .rar .7z", "설치 파일": ".dmg .pkg .exe .msi",
         "디자인": ".psd .ai .fig .sketch .indd .svg", "영상·소리": ".mp4 .mov .mp3 .wav", "폰트": ".ttf .otf .woff"}


def kind(name: str) -> str:
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return next((k for k, exts in KINDS.items() if ext and ext in exts.split()), "기타")


def all_files():
    root = folder()
    return [p for p in sorted(root.rglob("*")) if p.is_file() and not (set(p.relative_to(root).parts) & SKIP)]


@tool("📂", group="폴더 보기")
def list_files() -> str:
    """List files in the practice folder, one per line: [ID] path | size | modified date. You can pass the ID number to other tools."""
    from tools import STATE
    root, files = folder(), all_files()
    STATE["ids"] = {str(i): nfc(p.relative_to(root).as_posix()) for i, p in enumerate(files[:60], 1)}
    rows = [f"[{i}] {nfc(p.relative_to(root).as_posix())} | {p.stat().st_size // 1024}KB | "
            f"{datetime.fromtimestamp(p.stat().st_mtime):%Y-%m-%d}" for i, p in enumerate(files[:60], 1)]
    return f"파일 {len(files)}개\n" + "\n".join(rows) + ("\n…(60개까지만 보여 줌)" if len(files) > 60 else "")


@tool("🔍", group="폴더 보기")
def peek_file(path: str) -> str:
    """Peek at the first 500 characters of a text or PDF file. Images return only their size.

    Args:
        path: ID number or relative path from list_files
    """
    p = find(path)
    k = kind(p.name)
    if k == "이미지":
        try:
            from PIL import Image
            with Image.open(p) as im:
                return f"이미지 {im.width}x{im.height}, {p.stat().st_size // 1024}KB (내용은 보내지 않음)"
        except Exception:  # noqa: BLE001
            return f"이미지 {p.stat().st_size // 1024}KB (내용은 보내지 않음)"
    if p.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        r = PdfReader(str(p))
        return f"PDF {len(r.pages)}쪽. 첫 쪽: " + (r.pages[0].extract_text() or "(글자 없음)")[:500]
    if p.suffix.lower() in (".txt", ".md", ".csv", ".json", ".html"):
        return p.read_text(encoding="utf-8", errors="replace")[:500]
    return f"error: 읽을 수 없는 형식({p.suffix or '확장자 없음'}, {k}). 이름과 크기로 추리하세요."


@tool("ℹ️", group="폴더 보기")
def file_info(path: str) -> str:
    """Get kind, size and modified date of one file.

    Args:
        path: ID number or relative path from list_files
    """
    p = find(path)
    st = p.stat()
    return f"{nfc(p.name)} | 종류 {kind(p.name)} | {st.st_size // 1024}KB | 수정 {datetime.fromtimestamp(st.st_mtime):%Y-%m-%d %H:%M}"


@tool("🧮", group="폴더 보기")
def count_by_type() -> str:
    """Count files by kind (images, documents, archives ...)."""
    c = Counter(kind(p.name) for p in all_files())
    return "\n".join(f"{k}: {n}개" for k, n in c.most_common()) or "폴더가 비어 있습니다."
