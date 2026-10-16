"""도구 모음. 도구 하나 = 파이썬 함수 하나. 파일 하나에 비슷한 도구를 모읍니다.

새 도구 만들기 (예: tools/weather.py):

    from tools import tool

    @tool("🌦️", group="기타")
    def get_weather(city: str) -> str:
        \"\"\"Get today's weather for a city.\"\"\"     # ← 모델이 읽는 설명 (영어 한 줄)
        return "맑음, 21도"

그다음 agents/my-agent/agent.yaml 의 tools: 목록에 get_weather 를 넣으면 끝입니다.
규칙: 도구는 실패해도 예외를 던지지 말고 "error: 이유" 글을 돌려주세요. (던져도 엔진이 잡아 줍니다)
파일을 지우는 도구는 만들지 않습니다.
"""
import importlib
import pkgutil
import unicodedata
from pathlib import Path

TOOLS: dict = {}      # 이름 → {"func", "icon", "needs", "group", "module"}
STATE = {"folder": None, "ids": {}}  # 사본 폴더(엔진이 넣어 줌), list_files가 붙인 번호표


def tool(icon="🔧", needs=None, group="기타"):
    """함수를 도구로 등록합니다. needs="TAVILY_API_KEY" 처럼 필요한 키를 적으면 키가 없을 때 자동으로 꺼집니다."""
    def deco(func):
        TOOLS[func.__name__] = {
            "func": func, "icon": icon, "needs": needs, "group": group,
            "module": func.__module__.split(".")[-1],
        }
        return func
    return deco


def load_all():
    """tools/ 폴더의 모든 파일을 읽어 도구를 등록합니다. 파일 하나가 깨져도 나머지는 동작합니다."""
    errors = {}
    for m in pkgutil.iter_modules([str(Path(__file__).parent)]):
        if m.name.startswith("_"):
            continue
        try:
            importlib.reload(importlib.import_module(f"tools.{m.name}"))
        except Exception as e:  # noqa: BLE001
            errors[m.name] = f"{type(e).__name__}: {e}"
    return errors


def nfc(s: str) -> str:
    """한글 이름을 한 가지 방식(완성형, NFC)으로 맞춥니다. Mac은 자모로 쪼개 저장할 때가 있어서 필요합니다."""
    return unicodedata.normalize("NFC", s)


def folder() -> Path:
    f = STATE["folder"]
    if not f or not Path(f).is_dir():
        raise FileNotFoundError("사본 폴더가 아직 없습니다. 화면 위 [📁 폴더 고르기]를 먼저 눌러 주세요.")
    return Path(f)


def find(rel: str) -> Path:
    """사본 폴더 안의 파일을 찾습니다. list_files 번호('3', '[3]')도 받고, 한글 NFC/NFD 차이와
    작은 오타는 무시합니다. 밖으로 나가는 경로는 거부합니다."""
    root = folder().resolve()
    key = str(rel).strip().strip("[]# ")
    if key in STATE["ids"]:
        rel = STATE["ids"][key]
    rel = nfc(str(rel).strip().replace("\\", "/"))
    while rel.startswith("./"):
        rel = rel[2:]
    if not rel or rel.startswith(("/", "~")) or ".." in rel.split("/") or ":" in rel.split("/")[0]:
        raise PermissionError(f"사본 폴더 밖 경로는 쓸 수 없습니다: {rel}")
    cur = root
    for part in rel.split("/"):
        nxt = cur / part
        if not nxt.exists() and cur.is_dir():
            nxt = next((c for c in cur.iterdir() if nfc(c.name) == part), nxt)
        cur = nxt
    if not cur.exists():  # 모델이 이름을 조금 틀리게 쓴 경우(예: 한글이 깨짐) 가장 비슷한 이름을 찾습니다
        import difflib
        names = {nfc(p.relative_to(root).as_posix()): p for p in root.rglob("*") if p.is_file()}
        close = difflib.get_close_matches(rel, list(names), n=1, cutoff=0.6)
        if close:
            cur = names[close[0]]
    if not cur.exists():
        raise FileNotFoundError(f"'{rel}'을(를) 찾을 수 없습니다. list_files로 이름을 다시 확인하세요.")
    if root not in cur.resolve().parents and cur.resolve() != root:
        raise PermissionError("사본 폴더 밖 경로는 쓸 수 없습니다.")
    return cur
