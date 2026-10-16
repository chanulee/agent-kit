"""시험 1: 웹 검색 + 읽기 (Tavily MCP).

키 없이도 동작합니다. TAVILY_API_KEY가 있으면 서버에 넘깁니다.
Node와 npx가 필요합니다. 처음 실행 전에 `npx -y tavily-mcp@latest`를 한 번 받아 두면 안전합니다.
"""
import os

from aisuite.mcp import MCPClient

from common import run

env = None
if os.getenv("TAVILY_API_KEY"):
    # env를 넘기면 PATH 같은 기본 값이 빠질 수 있어서, 지금 환경 전체에 키를 더해 넘깁니다. [확인 필요]
    env = dict(os.environ)

mc = MCPClient(command="npx", args=["-y", "tavily-mcp@latest"], env=env)
try:
    tools = [t for t in mc.get_callable_tools() if t.__name__ in ("tavily_search", "tavily_extract")]
    ans, calls, dt = run(
        [{"role": "user", "content": "Search for Van Gogh Sunflowers, read the Korean Wikipedia article, "
                                     "summarize in 3 Korean sentences with source URL"}],
        tools,
    )
    for i, c in enumerate(calls, 1):
        print("call", i, c)
    print(f"time {dt:.1f}s\n", ans)
finally:
    mc.close()
