"""공통 실행기. PROVIDER=groq|gemini (기본 groq), MODEL로 덮어쓰기 가능."""
import os, re, time
import aisuite as ai
from aisuite.providers import openai_provider as _op

import kit  # .env 읽기 (ZAI_API_KEY, TAVILY_API_KEY)
PROVIDER = os.getenv("PROVIDER", "groq")
CFG = {
    "groq":   ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "openai:openai/gpt-oss-120b"),
    "zai":    ("https://api.z.ai/api/paas/v4/", "ZAI_API_KEY", "openai:glm-4.7-flash"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY", "openai:gemini-3.8-flash"),
}[PROVIDER]
MODEL = os.getenv("MODEL", CFG[2])
client = ai.Client({"openai": {"api_key": os.environ[CFG[1]], "base_url": CFG[0], "timeout": 60, "max_retries": 0}})

STATS = {"turns": 0, "r429": 0, "wait": 0.0, "in": 0, "out": 0}
_orig = _op.OpenaiProvider.chat_completions_create
def _wrapped(self, *a, **k):
    if PROVIDER == "zai": k.setdefault("extra_body", {"thinking": {"type": "disabled"}})
    for i in range(8):
        t = time.time()
        try:
            r = _orig(self, *a, **k)
        except Exception as e:
            s = str(e)
            if "429" not in s and "503" not in s: raise
            if os.getenv("STOP_ON_429","1")=="1":
                STATS["r429"]+=1; print("  [429/503] 재시도 없이 중단", flush=True); raise
            m = re.search(r"(?:try again in|retry in) ([\d.]+)(ms|s)", s)
            w = (float(m.group(1)) / (1000 if m.group(2) == "ms" else 1) + 1) if m else 15
            STATS["r429"] += 1; STATS["wait"] += w
            print(f"  [{'429' if '429' in s else '503'}] {w:.1f}s 대기 후 재시도", flush=True); time.sleep(w); continue
        STATS["turns"] += 1
        u = getattr(r, "usage", None)
        if u: STATS["in"] += u.prompt_tokens or 0; STATS["out"] += u.completion_tokens or 0
        tc = r.choices[0].message.tool_calls or []
        names = [c.function.name for c in tc]
        print(f"  turn {STATS['turns']}: {time.time()-t:.1f}s, tokens in/out={getattr(u,'prompt_tokens',None)}/{getattr(u,'completion_tokens',None)}, tools={names or '없음(최종답)'}", flush=True)
        return r
    raise RuntimeError("재시도 초과")
_op.OpenaiProvider.chat_completions_create = _wrapped

def run(msgs, tools, max_turns=8):
    print(f"provider={PROVIDER} model={MODEL}", flush=True)
    msgs = list(msgs)
    ko = "\n항상 한국어로 답해."
    if msgs and msgs[0]["role"] == "system": msgs[0] = {**msgs[0], "content": msgs[0]["content"] + ko}
    else: msgs.insert(0, {"role": "system", "content": ko.strip()})
    if os.getenv("EXTRA_RULES") == "1":
        rules = "\n규칙: 도구 결과가 없으면 2번까지만 다시 시도하고, 그래도 없으면 멈추고 지금까지 아는 것으로 답해.\n규칙: apply_move는 승인을 스스로 처리하니, 채팅으로 허락을 묻지 말고 바로 apply_move를 호출해."
        msgs = list(msgs)
        if msgs and msgs[0]["role"] == "system": msgs[0] = {**msgs[0], "content": msgs[0]["content"] + rules}
        else: msgs.insert(0, {"role": "system", "content": rules.strip()})
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
    print(f"STATS {STATS} total={dt:.1f}s", flush=True)
    import json; json.dump(STATS, open(os.getenv("STATS_FILE","/tmp/last_stats.json"),"w"))
    return r.choices[0].message.content, calls, dt
