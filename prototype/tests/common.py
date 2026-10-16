"""시험 3종이 같이 쓰는 부분: 모델 연결, 재시도, 실행 결과 정리.

키는 환경 변수에서만 읽습니다. 이 파일에 키를 적지 마세요.
- Gemini(시험에서 쓴 방식): GEMINI_API_KEY, MODEL=openai:gemini-3.5-flash 등
- Anthropic(아직 시험 안 함): ANTHROPIC_API_KEY, MODEL=anthropic:<모델 ID>
"""
import os
import re
import time

import aisuite as ai

MODEL = os.getenv("MODEL", "openai:gemini-3.8-flash")

if MODEL.startswith("anthropic:"):
    # [확인 필요] Anthropic으로는 아직 처음부터 끝까지 돌려 보지 않았습니다.
    client = ai.Client({"anthropic": {"api_key": os.environ["ANTHROPIC_API_KEY"]}})
else:
    # aisuite의 "gemini:" 방식은 도구 호출 때 400 오류(thought_signature 없음)가 납니다.
    # 그래서 Gemini를 OpenAI 호환 주소로 부릅니다.
    client = ai.Client({
        "openai": {
            "api_key": os.environ["GEMINI_API_KEY"],
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        }
    })


def run(msgs, tools, max_turns=8):
    """도구 루프를 돌리고 (최종 답, 도구 호출 목록, 걸린 초)를 돌려줍니다."""
    t = time.time()
    r = client.chat.completions.create(model=MODEL, messages=msgs, tools=tools, max_turns=max_turns)
    dt = time.time() - t
    calls = []
    for m in r.choices[0].intermediate_messages:
        tc = m.get("tool_calls") if isinstance(m, dict) else getattr(m, "tool_calls", None)
        for c in tc or []:
            f = c["function"] if isinstance(c, dict) else c.function
            n = f["name"] if isinstance(f, dict) else f.name
            a = f["arguments"] if isinstance(f, dict) else f.arguments
            calls.append((n, str(a)[:120]))
    return r.choices[0].message.content, calls, dt


# 429(호출 한도)나 503(서버 바쁨)이면 기다렸다 다시 시도합니다.
# 시험 당시에는 429만 처리했고, 503 처리는 이후 결정에 따라 더했습니다(다시 돌려 보지 않음).
def _patch_retry(provider_cls):
    orig = provider_cls.chat_completions_create

    def _retry(self, *a, **k):
        for _ in range(6):
            try:
                return orig(self, *a, **k)
            except Exception as e:  # 공급자마다 오류 종류가 달라서 글로 판단합니다
                msg = str(e)
                if "429" not in msg and "503" not in msg:
                    raise
                if "PerDay" in msg or re.search(r"retry in \d+h", msg):
                    # 하루 한도를 다 쓴 경우: 기다려도 소용없으므로 바로 멈춥니다.
                    raise RuntimeError("하루 호출 한도를 다 썼습니다. 유료 키나 다른 모델을 쓰세요.") from e
                m = re.search(r"retry in ([\d.]+)s", msg)
                w = float(m.group(1)) + 1 if m else 20
                code = "429" if "429" in msg else "503"
                print(f"  [{code}] {w:.0f}초 기다리는 중")
                time.sleep(w)
        return orig(self, *a, **k)

    provider_cls.chat_completions_create = _retry


from aisuite.providers import openai_provider as _op  # noqa: E402
_patch_retry(_op.OpenaiProvider)
