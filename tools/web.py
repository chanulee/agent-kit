"""웹 도구: Tavily MCP. 주소와 켜고 끄기는 저장소 루트의 mcp.json 에 있습니다.

.env 의 TAVILY_API_KEY 에는 키(tvly-...)만 넣어도 되고, Tavily MCP 주소 전체를 넣어도 됩니다.
mcp.json 에서 tavily 가 꺼져 있으면 이 도구들은 목록에 나와도 동작하지 않습니다.
"""
import json
import os
import re
import threading
from pathlib import Path

from tools import tool

ROOT = Path(__file__).resolve().parent.parent
SEEN_URLS: set = set()   # 이번 실행에서 실제로 받은 주소 (갤러리 출처 검사용)
_client = {"mcp": None, "tools": {}, "url": ""}
_lock = threading.Lock()


def load_mcp() -> dict:
    """mcp.json 을 읽습니다. 없거나 깨져 있으면 빈 설정으로 봅니다."""
    path = ROOT / "mcp.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _env_value() -> str:
    return os.environ.get("TAVILY_API_KEY", "").strip().strip('"').strip("'")


def _key() -> str:
    """로그에서 가릴 키. 주소 전체를 넣었으면 그 안의 tavilyApiKey 만 뽑습니다."""
    v = _env_value()
    m = re.search(r"tavilyApiKey=([^&\s]+)", v)
    return m.group(1) if m else v


def server_url() -> str:
    """접속 주소. .env 가 http 로 시작하면 그 주소를 쓰고, 키만 있으면 mcp.json 의 url 에 넣습니다."""
    v = _env_value()
    if v.startswith(("http://", "https://")):
        return v
    cfg = load_mcp().get("tavily") or {}
    template = str(cfg.get("url") or "https://mcp.tavily.com/mcp/?tavilyApiKey=${TAVILY_API_KEY}")
    return template.replace("${TAVILY_API_KEY}", v)


def redact(text) -> str:
    text, k = str(text), _key()
    return text.replace(k, "***") if k else text


def _tavily():
    with _lock:
        url = server_url()
        if _client["mcp"] is None or _client["url"] != url:
            from aisuite.mcp import MCPClient
            _client["mcp"] = MCPClient(server_url=url, name="tavily")
            _client["tools"] = {t.__name__: t for t in _client["mcp"].get_callable_tools()}
            _client["url"] = url
        return _client["tools"]


def _call(name: str, **kw) -> str:
    out = redact(_tavily()[name](**kw))
    SEEN_URLS.update(u.rstrip(").,;'\"") for u in re.findall(r"https?://[^\s\"'<>\]]+", out))
    SEEN_URLS.update(kw.get("urls") or [])
    return out[:4000]


@tool("🌐", needs="TAVILY_API_KEY", group="웹")
def web_search(query: str) -> str:
    """Search the web. Returns top 3 results (title, url, snippet).

    Args:
        query: a non-empty search phrase
    """
    if not query.strip():
        return "error: 검색어가 비어 있습니다. 예: 'Van Gogh Sunflowers'"
    cfg = load_mcp().get("tavily") or {}
    if not cfg.get("enabled"):
        return "error: mcp.json에서 Tavily가 꺼져 있습니다. 웹 검색을 쓰려면 그 파일에서 켜세요."
    return _call("tavily_search", query=query, max_results=3)


@tool("📖", needs="TAVILY_API_KEY", group="웹")
def web_read(url: str) -> str:
    """Read the main text of one web page (e.g. a Wikipedia article) by its full URL.

    Args:
        url: full URL starting with http
    """
    if not url.startswith("http"):
        return "error: http로 시작하는 전체 주소를 주세요."
    cfg = load_mcp().get("tavily") or {}
    if not cfg.get("enabled"):
        return "error: mcp.json에서 Tavily가 꺼져 있습니다. 페이지를 읽으려면 그 파일에서 켜세요."
    return _call("tavily_extract", urls=[url])
