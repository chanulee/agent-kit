"""웹 손: Tavily 원격 MCP(설치 없음). .env 의 TAVILY_API_KEY 가 없으면 이 손들은 자동으로 꺼집니다.

TAVILY_API_KEY 에는 키(tvly-...)만 넣어도 되고, Tavily가 준 MCP 주소 전체를 넣어도 됩니다.
"""
import os
import re
import threading

from hands import hand

SEEN_URLS: set = set()   # 이번 실행에서 실제로 받은 주소 (갤러리 출처 검사용)
_client = {"mcp": None, "tools": {}}
_lock = threading.Lock()


def _key() -> str:
    v = os.environ.get("TAVILY_API_KEY", "").strip().strip('"')
    m = re.search(r"tavilyApiKey=([^&\s]+)", v)
    return m.group(1) if m else v


def redact(text) -> str:
    text, k = str(text), _key()
    return text.replace(k, "***") if k else text


def _tavily():
    with _lock:
        if _client["mcp"] is None:
            from aisuite.mcp import MCPClient
            _client["mcp"] = MCPClient(server_url=f"https://mcp.tavily.com/mcp/?tavilyApiKey={_key()}", name="tavily")
            _client["tools"] = {t.__name__: t for t in _client["mcp"].get_callable_tools()}
        return _client["tools"]


def _call(name: str, **kw) -> str:
    out = redact(_tavily()[name](**kw))
    SEEN_URLS.update(u.rstrip(").,;'\"") for u in re.findall(r"https?://[^\s\"'<>\]]+", out))
    SEEN_URLS.update(kw.get("urls") or [])
    return out[:4000]


@hand("🌐", needs="TAVILY_API_KEY")
def web_search(query: str) -> str:
    """Search the web. Returns top 3 results (title, url, snippet).

    Args:
        query: a non-empty search phrase
    """
    if not query.strip():
        return "error: 검색어가 비어 있습니다. 예: 'Van Gogh Sunflowers'"
    return _call("tavily_search", query=query, max_results=3)


@hand("📖", needs="TAVILY_API_KEY")
def web_read(url: str) -> str:
    """Read the main text of one web page (e.g. a Wikipedia article) by its full URL.

    Args:
        url: full URL starting with http
    """
    if not url.startswith("http"):
        return "error: http로 시작하는 전체 주소를 주세요."
    return _call("tavily_extract", urls=[url])
