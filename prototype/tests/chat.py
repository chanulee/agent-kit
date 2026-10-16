"""대화 시험: 에이전트와 그냥 대화하고, 링크를 주면 읽게 해 봅니다.

실행 (prototype/tests 폴더에서):
    python chat.py
준비: 같은 폴더의 .env 에 ZAI_API_KEY=..., TAVILY_API_KEY=... (TAVILY는 링크 읽기·검색에 필요)

- 링크를 보내면 web_read(Tavily extract)로 읽습니다. 웹 검색은 web_search.
- 매 턴마다 어떤 도구를 불렀는지, 몇 초 걸렸는지 화면에 찍힙니다.
- 끝내려면 빈 줄에서 Enter 또는 Ctrl+C.
"""
import os
import sys

import kit  # .env 읽기

if not os.getenv("PROVIDER") and os.getenv("ZAI_API_KEY"):
    os.environ["PROVIDER"] = "zai"
need = {"zai": "ZAI_API_KEY", "groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY"}[os.getenv("PROVIDER", "groq")]
if not os.getenv(need):
    sys.exit(f"모델 키가 없습니다({need}).\n이 폴더의 .env 파일에 {need}=... 를 넣고 다시 실행하세요.")
os.environ.setdefault("STOP_ON_429", "0")  # 대화에서는 429가 나면 기다렸다 다시 시도

from common import run  # noqa: E402

tools = [kit.web_search, kit.web_read] if os.getenv("TAVILY_API_KEY") else []
if not tools:
    print("(TAVILY_API_KEY가 없어서 웹 도구 없이 대화만 합니다)")
SYSTEM = ("너는 디자인 전공 학생을 돕는 한국어 에이전트야. 짧고 분명하게 답해. "
          "사용자가 링크(URL)를 주면 web_read로 실제로 읽고 나서 답하고, 출처 URL을 적어. "
          "모르는 최신 정보는 web_search로 찾아. 도구가 error를 돌려주면 이유를 말하고 다른 방법을 써.")
history = [{"role": "system", "content": SYSTEM}]

print("에이전트와 대화합니다. 링크를 붙여 넣으면 읽어 봅니다. (끝내기: 빈 줄 Enter)\n")
try:
    while True:
        text = input("나> ").strip()
        if not text:
            break
        history.append({"role": "user", "content": text})
        kit.WEB_CALLS.clear()  # 웹 호출 한도는 한 번의 질문마다 다시 셉니다
        try:
            ans, calls, dt = run(history, tools, max_turns=6)
        except Exception as e:  # 어떤 단계에서 무슨 오류인지 보여 주고 대화는 계속
            print(f"\n[오류] 모델을 부르다 실패했습니다: {type(e).__name__}: {kit.redact(e)[:300]}\n"
                  "다시 보내 보거나, 키·인터넷을 확인하세요.\n")
            history.pop()
            continue
        for i, (name, args) in enumerate(calls, 1):
            print(f"  도구 {i}: {name} {args}")
        print(f"\n에이전트> {ans}\n  ({dt:.1f}초)\n")
        history.append({"role": "assistant", "content": ans or ""})
except (KeyboardInterrupt, EOFError):
    pass
finally:
    kit.close_web()
