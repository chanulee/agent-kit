"""엔진(하네스). 학생은 이 파일을 고치지 않습니다. 부품(agents/, tools/, skills/, mcp.json, config.yaml)만 바꿉니다.

루프는 aisuite가 돌립니다: Runner.run_sync(agent, ...) 안에서 "모델 → 도구 → 결과 → 다시 모델"을 max_turns까지.
엔진이 하는 일은 그 루프에 네 가지를 끼우는 것뿐입니다.
  1) 보이기   : aisuite가 내보내는 이벤트(TraceSink)를 대시보드와 runs/<시간>/trace.jsonl 로 보냄
  2) 승인     : aisuite tool_policy 자리에서 화면 버튼을 기다림 (agent.yaml 의 ask_before)
  3) 루프 조절: 도구를 감싸서 횟수 제한(limits), 같은 호출 막기(no_repeat), 오류를 글로 바꾸기
  4) 기다렸다 다시: 429/503이면 기다리는 시간을 보여 주고 다시 부름 (retry)
"""
import functools
import json
import os
import queue
import re
import threading
import time
from datetime import datetime
from pathlib import Path

import aisuite as ai
from aisuite.agents.types import ToolPolicyDecision
from aisuite.providers import openai_provider
from ruamel.yaml import YAML

import tools
import tools.files
from tools import move

ROOT = Path(__file__).resolve().parent.parent
yaml = YAML()
yaml.preserve_quotes = True
KEYS = ("ZAI_API_KEY", "TAVILY_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY")


# ───────────────────────── 설정 읽고 쓰기 ─────────────────────────

def read_yaml(path: Path) -> dict:
    return json.loads(json.dumps(yaml.load(path.read_text(encoding="utf-8")) or {}))


def set_yaml(path: Path, key: str, value) -> None:
    """주석을 지키며 값 하나만 바꿉니다."""
    doc = yaml.load(path.read_text(encoding="utf-8"))
    doc[key] = value
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(doc, f)


def config() -> dict:
    c = read_yaml(ROOT / "config.yaml")
    c.setdefault("agent", "my-agent")
    c.setdefault("team_partner", "docent")
    c["folder_path"] = Path(os.path.expanduser(c.get("folder", "~/agent-workshop/copy")))
    return c


def load_agent(name: str) -> dict:
    d = ROOT / "agents" / name
    a = read_yaml(d / "agent.yaml")
    a.update(name=name, persona=(d / "persona.md").read_text(encoding="utf-8"))
    for k, v in {"title": name, "tools": [], "max_turns": 8, "limits": {}, "no_repeat": True,
                 "ask_before": [], "retry": 4, "remember_tool_results": False, "skills": []}.items():
        a.setdefault(k, v)
    a["skill_text"] = "\n\n".join((ROOT / "skills" / s / "SKILL.md").read_text(encoding="utf-8")
                                  for s in a["skills"] if (ROOT / "skills" / s / "SKILL.md").exists())
    return a


def load_mcp() -> dict:
    path = ROOT / "mcp.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def tool_status() -> dict:
    """모든 도구와 켜짐 여부. MCP가 꺼져 있거나 필요한 키가 없으면 이유와 함께 꺼짐."""
    errors = tools.load_all()
    mcp_tools = {}
    for srv, cfg in load_mcp().items():
        if isinstance(cfg, dict):
            for n in cfg.get("tools") or []:
                mcp_tools[n] = {"server": srv, "enabled": bool(cfg.get("enabled"))}
    out = {}
    for n, h in tools.TOOLS.items():
        item = {"icon": h["icon"], "module": h["module"], "group": h.get("group") or "기타", "ok": True, "why": ""}
        if n in mcp_tools and not mcp_tools[n]["enabled"]:
            item.update(ok=False, why=f"mcp.json에서 {mcp_tools[n]['server']}가 꺼져 있습니다")
        elif h["needs"] and not os.environ.get(h["needs"]):
            item.update(ok=False, why=f".env에 {h['needs']}가 없어서 꺼짐")
        out[n] = item
    for mod, err in errors.items():
        out[f"({mod}.py)"] = {"icon": "⚠️", "module": mod, "group": "기타", "ok": False, "why": f"파일 오류: {err}"}
    return out


# ───────────────────────── 이벤트 (보이기) ─────────────────────────

def redact(text: str) -> str:
    for k in KEYS:
        v = os.environ.get(k, "")
        if len(v) > 6:
            text = text.replace(v, "***")
    return re.sub(r"tavilyApiKey=[^&\s'\"]+", "tavilyApiKey=***", text)


class Bus:
    def __init__(self):
        self.subs: list[queue.Queue] = []
        self.file: Path | None = None
        self.lock = threading.Lock()

    def new_run(self):
        d = ROOT / "runs" / datetime.now().strftime("%Y%m%d-%H%M%S")
        d.mkdir(parents=True, exist_ok=True)
        self.file = d / "trace.jsonl"

    def emit(self, kind: str, data=None, agent: str = ""):
        ev = {"event_type": kind, "time": time.time(), "agent": agent, "data": data or {}}
        line = redact(json.dumps(ev, ensure_ascii=False, default=str))
        if self.file:
            with self.lock, self.file.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        for q in list(self.subs):
            q.put(json.loads(line))


class DashboardSink:
    """aisuite TraceSink: aisuite가 루프를 돌며 내보내는 이벤트를 대시보드로 넘깁니다."""
    def __init__(self, bus: Bus, agent: str):
        self.bus, self.agent = bus, agent

    def emit(self, event):
        d = event.to_dict()
        self.bus.emit(d["event_type"], d.get("data") or {}, self.agent)


# ───────────────────────── 오류 카드 (투명하게) ─────────────────────────

class StepError(Exception):
    """어느 단계에서, 무슨 일이, 학생은 무엇을 하면 되는지."""
    def __init__(self, stage, what, todo, raw=""):
        super().__init__(what)
        self.card = {"stage": stage, "what": what, "todo": todo, "raw": redact(str(raw))[:400]}


def to_card(e: Exception) -> dict:
    if isinstance(e, StepError):
        return e.card
    s = str(e)
    code = re.search(r"Error code: (\d{3})", s)
    code = code.group(1) if code else ""
    if code == "401" or "incorrect" in s or "invalid api key" in s.lower():
        return StepError("모델 호출", "모델 키가 맞지 않습니다 (401)", ".env의 키를 다시 붙여 넣고 앱을 다시 켜세요", s).card
    if code in ("429", "503") or "rate limit" in s.lower():
        return StepError("모델 호출", f"서버가 계속 바쁩니다 ({code or '429'})", "1분쯤 뒤 [다시 시도]를 누르세요", s).card
    if code == "404" or "model" in s.lower() and "not" in s.lower() and "found" in s.lower():
        return StepError("모델 호출", "모델 이름을 찾을 수 없습니다", "config.yaml의 model 철자를 확인하세요", s).card
    if code == "400":
        return StepError("모델 호출", "모델이 요청을 거절했습니다 (400)", "[새 대화]를 누르고 다시 해 보세요", s).card
    if "connect" in s.lower() or "timed out" in s.lower() or "timeout" in s.lower():
        return StepError("모델 호출", "모델 서버에 연결하지 못했습니다", "와이파이를 확인하고 [다시 시도]", s).card
    return StepError("엔진", f"예상하지 못한 문제: {type(e).__name__}", "[다시 시도]를 누르고, 또 나면 강사에게 화면을 보여 주세요", s).card


# ───────────────────────── 기다렸다 다시 (retry) ─────────────────────────

_run = threading.local()  # 지금 실행 중인 판의 정보 (조절값, 멈춤 여부)
_orig_create = openai_provider.OpenaiProvider.chat_completions_create


def _create_with_retry(self, *a, **k):
    r = getattr(_run, "ctx", None)
    tries = (r.retry if r else 4) + 1
    for i in range(tries):
        try:
            return _orig_create(self, *a, **k)
        except Exception as e:  # noqa: BLE001
            s = str(e)
            if not re.search(r"\b(429|503|502|500)\b", s) or i == tries - 1 or r is None:
                raise
            if "per day" in s.lower() or "PerDay" in s:
                raise StepError("모델 호출", "오늘 쓸 수 있는 호출 한도를 다 썼습니다", "다른 키로 바꾸거나 강사에게 알려 주세요", s)
            m = re.search(r"(?:try again in|retry in) ([\d.]+)(ms|s)", s)
            wait = min(60.0, float(m.group(1)) / (1000 if m.group(2) == "ms" else 1) + 1) if m else 5.0 * (i + 1)
            r.bus.emit("retry.waiting", {"wait_s": round(wait), "attempt": i + 1, "max": tries - 1,
                                         "code": re.search(r"\b(429|503|502|500)\b", s).group(1)}, r.agent)
            end = time.time() + wait
            while time.time() < end:
                if r.cancel.is_set():
                    raise StepError("모델 호출", "멈춤", "다시 보내세요")
                time.sleep(0.2)
    raise RuntimeError("unreachable")


openai_provider.OpenaiProvider.chat_completions_create = _create_with_retry

# aisuite는 도구 결과를 json.dumps로 감싸면서 한글을 \uXXXX로 바꿉니다(토큰이 몇 배로 늘고 로그도 못 읽음).
# 한글을 그대로 두도록 aisuite 도구 모듈의 json.dumps 기본값만 바꿉니다.
import aisuite.utils.tools as _ai_tools  # noqa: E402


class _KoreanJson:
    def __getattr__(self, name):
        return getattr(json, name)

    @staticmethod
    def dumps(obj, **kw):
        kw.setdefault("ensure_ascii", False)
        return json.dumps(obj, **kw)


_ai_tools.json = _KoreanJson()


# ───────────────────────── 한 판 실행 ─────────────────────────

class Ctx:
    """한 에이전트가 한 질문을 처리하는 동안의 상태."""
    def __init__(self, engine, agent: dict):
        self.bus, self.cancel, self.engine = engine.bus, engine.cancel, engine
        self.agent, self.retry = agent["name"], int(agent["retry"])
        self.limits = agent["limits"] or {}
        self.no_repeat, self.ask_before = agent["no_repeat"], set(agent["ask_before"] or [])
        self.counts: dict = {}
        self.cache: dict = {}
        self.calls = 0

    def wrap(self, name: str):
        """도구를 감쌉니다: 멈춤 · 횟수 제한 · 같은 호출 막기 · 오류를 글로."""
        func = tools.TOOLS[name]["func"]

        @functools.wraps(func)
        def wrapper(**kwargs):
            if self.cancel.is_set():
                return "error: 사용자가 멈췄습니다. 더 진행하지 말고 지금까지 한 일을 짧게 말하세요."
            group = "web" if name.startswith("web_") else name
            limit = self.limits.get(group)
            key = name + json.dumps(kwargs, sort_keys=True, ensure_ascii=False)
            if self.no_repeat and key in self.cache:
                self.bus.emit("loop.repeat_blocked", {"tool": name}, self.agent)
                return "(같은 호출을 이미 했습니다. 다시 실행하지 않았어요. 아래는 그때 결과입니다)\n" + self.cache[key]
            if limit is not None and self.counts.get(group, 0) >= int(limit):
                self.bus.emit("loop.limit", {"tool": name, "limit": limit}, self.agent)
                return f"error: '{group}' 도구는 이번 질문에서 {limit}번까지만 쓸 수 있습니다. 가진 정보로 답하세요."
            self.counts[group] = self.counts.get(group, 0) + 1
            self.calls += 1
            try:
                out = func(**kwargs)
                out = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False, default=str)
            except Exception as e:  # noqa: BLE001 - 도구가 터져도 루프는 계속 (aisuite는 예외면 전체가 멈춤)
                out = f"error: [{name}] {type(e).__name__}: {redact(str(e))[:300]}"
            if self.no_repeat and not out.startswith("error:"):
                self.cache[key] = out
            return out
        return wrapper

    def policy(self, pctx):
        """aisuite tool_policy: ask_before에 있는 도구는 화면 버튼을 기다립니다."""
        if pctx.tool_name not in self.ask_before:
            return True
        args = dict(pctx.arguments or {})
        view = {"tool": pctx.tool_name, "args": args}
        if pctx.tool_name == "move_files":
            plan = move.review_card(args.get("plan_id", ""))
            if not plan:
                return ToolPolicyDecision(allowed=False, reason="심사 중인 계획이 없습니다. propose_plan으로 계획을 먼저 세우세요.")
            if args.get("plan_id") and args["plan_id"] != plan["plan_id"]:
                # 모델이 번호를 잘못 기억함 → 지금 계획을 씁니다. 숨기지 않고 루프 칸에 보여 줍니다.
                self.bus.emit("loop.plan_id_fixed", {"given": args["plan_id"], "used": plan["plan_id"]}, self.agent)
            view["plan"] = plan
        if pctx.tool_name == "write_file":
            content = str(args.get("content") or "")
            view["preview"] = {"path": str(args.get("path") or ""), "content": content[:4000], "chars": len(content)}
            view["args"] = {"path": view["preview"]["path"], "chars": len(content)}
        decision = self.engine.ask_human(view, self.agent)
        if pctx.tool_name == "move_files":
            ok, why = move.apply_review(plan["plan_id"], decision)
            return True if ok else ToolPolicyDecision(allowed=False, reason=why)
        if decision.get("action") == "approve":
            return True
        return ToolPolicyDecision(allowed=False, reason="사용자가 거절했습니다. " + (decision.get("comment") or ""))


class Engine:
    def __init__(self, client=None):
        self.bus = Bus()
        self.cancel = threading.Event()
        self.busy = threading.Lock()
        self.history: dict[str, list] = {}
        self.pending: dict[str, dict] = {}
        self.client = client  # 시험에서는 가짜 클라이언트를 넣습니다

    # ── 사람 승인 ──
    def ask_human(self, view: dict, agent: str) -> dict:
        aid = f"a{int(time.time() * 1000)}"
        box = {"view": view, "done": threading.Event(), "answer": None}
        self.pending[aid] = box
        self.bus.emit("approval.requested", {"id": aid, **view}, agent)
        while not box["done"].wait(0.25):
            if self.cancel.is_set():
                box["answer"] = {"action": "deny", "comment": "멈춤"}
                break
        self.pending.pop(aid, None)
        self.bus.emit("approval.resolved", {"id": aid, "answer": box["answer"]}, agent)
        return box["answer"]

    def answer(self, aid: str, decision: dict) -> bool:
        box = self.pending.get(aid)
        if not box:
            return False
        box["answer"] = decision
        box["done"].set()
        return True

    # ── 모델 연결 ──
    def make_client(self, cfg):
        if self.client:
            return self.client
        key = os.environ.get(cfg.get("key_env", "ZAI_API_KEY"), "").strip().strip('"')
        if not key:
            raise StepError("준비", f"모델 키가 없습니다 ({cfg.get('key_env')})",
                            "키트 폴더의 .env 파일에 키를 붙여 넣고 앱을 다시 켜세요")
        return ai.Client({"openai": {"api_key": key, "base_url": cfg.get("base_url"), "timeout": 90, "max_retries": 0}})

    def run_agent(self, name: str, text: str, cfg: dict, keep_history=True) -> str:
        a = load_agent(name)
        ctx = Ctx(self, a)
        _run.ctx = ctx
        status = tool_status()
        picked = [ctx.wrap(n) for n in a["tools"] if status.get(n, {}).get("ok")]
        off = [n for n in a["tools"] if not status.get(n, {}).get("ok")]
        instructions = a["persona"] + ("\n\n" + a["skill_text"] if a["skill_text"] else "") + "\n\n항상 한국어로 답해."
        self.bus.emit("agent.start", {"title": a["title"], "tools": [t.__name__ for t in picked], "tools_off": off,
                                      "knobs": {k: a[k] for k in ("max_turns", "limits", "no_repeat", "ask_before",
                                                                  "retry", "remember_tool_results")},
                                      "skills": a["skills"], "context_chars": len(instructions)}, name)
        if a["skill_text"]:
            self.bus.emit("skill.loaded", {"skills": a["skills"], "chars": len(a["skill_text"])}, name)
        settings = {"extra_body": {"thinking": {"type": "disabled"}}} if "z.ai" in str(cfg.get("base_url")) else {}
        agent = ai.Agent(name=name, model=cfg["model"], instructions=instructions, tools=picked, model_settings=settings)
        hist = self.history.setdefault(name, []) if keep_history else []
        msgs = hist + [{"role": "user", "content": text}]
        try:
            res = ai.Runner.run_sync(agent, msgs, client=self.make_client(cfg), max_turns=int(a["max_turns"]),
                                     trace_sinks=[DashboardSink(self.bus, name)], tool_policy=ctx.policy)
        finally:
            _run.ctx = None
        last = res.raw_responses[-1].choices[0].message if res.raw_responses else None
        answer = (res.final_output or "").strip()
        if last is not None and getattr(last, "tool_calls", None):
            # 턴 한도에 닿았습니다. 도구 없이 한 번만 더 불러 "지금까지 알아낸 것"으로 답하게 합니다.
            self.bus.emit("run.max_turns", {"max_turns": a["max_turns"]}, name)
            wrap = ai.Agent(name=name, model=cfg["model"], instructions=instructions, model_settings=settings)
            msgs2 = [m for m in res.messages if m.get("role") != "system"]
            if msgs2 and msgs2[-1].get("tool_calls"):
                msgs2 = msgs2[:-1]  # 실행되지 못한 마지막 도구 호출은 뺍니다
            msgs2.append({"role": "user", "content": f"턴 한도({a['max_turns']})에 닿았어. 도구는 더 못 써. "
                                                      "지금까지 알아낸 것만으로 짧게 답해."})
            _run.ctx = ctx
            try:
                answer = (ai.Runner.run_sync(wrap, msgs2, client=self.make_client(cfg), max_turns=1,
                                             trace_sinks=[DashboardSink(self.bus, name)]).final_output or "").strip()
            finally:
                _run.ctx = None
            answer = answer or f"(턴 한도 {a['max_turns']}에 도달해서 멈췄습니다)"
        if ctx.calls == 0 and re.search(r"(읽어 ?봤|읽었|찾아 ?봤|검색해 ?봤|접속|확인해 ?봤|읽으려)", answer):
            self.bus.emit("warn.says_but_no_action", {"text": "답에는 '해 봤다'는 말이 있지만 도구를 한 번도 쓰지 않았어요."}, name)
        if keep_history:
            if a["remember_tool_results"]:
                hist[:] = [m for m in res.messages if m.get("role") != "system"]
            else:
                hist += [{"role": "user", "content": text}, {"role": "assistant", "content": answer}]
        return answer

    def _prepare(self):
        cfg = config()
        tools.STATE["folder"] = cfg["folder_path"]
        from tools.web import SEEN_URLS
        SEEN_URLS.clear()
        return cfg

    def run(self, text: str, mode: str = "chat") -> str:
        """화면에서 메시지 하나가 왔을 때. mode='team' 이면 나의 에이전트 다음 도슨트 순서로 돕니다."""
        if not self.busy.acquire(blocking=False):
            raise StepError("준비", "아직 이전 질문을 처리 중입니다", "끝나거나 [멈춤]을 누른 뒤 보내세요")
        self.cancel.clear()
        self.bus.new_run()
        try:
            cfg = self._prepare()
            label = "팀 실행" if mode == "team" else "대화"
            self.bus.emit("chat.user", {"text": text, "mode": label})
            try:
                if mode == "team":
                    answer = self._team(text, cfg)
                else:
                    answer = self.run_agent(cfg["agent"], text, cfg)
                    self.bus.emit("chat.reply", {"text": answer, "agent": cfg["agent"]})
                return answer
            except Exception as e:  # noqa: BLE001
                card = to_card(e)
                self.bus.emit("error.card", card)
                return f"❌ [{card['stage']}] {card['what']} → {card['todo']}"
        finally:
            self.bus.emit("run.end", {})
            self.busy.release()

    def _team(self, text: str, cfg: dict) -> str:
        """코드가 정한 순서: 학생 에이전트가 정리하고, 도슨트가 갤러리를 만듭니다."""
        student = cfg["agent"]
        partner = cfg.get("team_partner") or "docent"
        steps = []
        for name, job in ((student, "폴더 정리"), (partner, "갤러리")):
            steps.append({"name": name, "title": load_agent(name)["title"], "job": job})
        self.bus.emit("team.start", {"steps": steps})
        folder = cfg["folder_path"]
        before = [p.relative_to(folder).as_posix() for p in folder.iterdir() if p.is_file()] if folder.is_dir() else []
        tidy = (text + "\n\n(팀 1단계 · 폴더 정리) 폴더를 살펴보세요. "
                "스킬이 켜져 있으면 그 규칙대로 정리 계획을 세우세요. "
                "파일을 옮기는 도구가 있으면 화면 승인을 받은 뒤 옮기세요. "
                "계획 도구만 있으면 계획은 세우고 옮기지는 마세요. "
                "볼 수 있는 도구가 없으면 모른다고 말하세요.")
        prev, answers = "", []
        for i, step in enumerate(steps):
            if self.cancel.is_set():
                break
            self.bus.emit("team.step", {**step, "status": "running"})
            if i:
                self.bus.emit("agent.handoff", {
                    "from": steps[i - 1]["name"], "to": step["name"],
                    "from_title": steps[i - 1]["title"], "to_title": step["title"],
                    "passed": prev[:500],
                })
            try:
                files = ", ".join(p.relative_to(folder).as_posix() for p in tools.files.all_files()) or "(파일 없음)"
            except (FileNotFoundError, OSError):
                files = "(사본 폴더가 아직 없습니다)"
            if i == 0:
                prompt = tidy
            else:
                prompt = ("(팀 2단계 · 갤러리) 앞 에이전트의 결과:\n" + prev[:800]
                          + "\n\n정리된 파일:\n" + files
                          + "\n\n사용자에게 묻지 말고 바로 갤러리를 만드세요. "
                          "작품의 제목·작가·연도·이미지는 met_search가 준 값만 쓰세요. "
                          "출처는 이번에 웹에서 실제로 받은 주소만 넣으세요. 웹 도구가 꺼져 있으면 출처는 비우세요.")
            prev = self.run_agent(step["name"], prompt, cfg, keep_history=False)
            answers.append(f"{step['title']}: {prev}")
            self.bus.emit("chat.reply", {"text": f"{step['title']}\n{prev}", "agent": step["name"]})
            self.bus.emit("team.step", {**step, "status": "done", "summary": prev[:240]})
            if i == 0 and folder.is_dir():
                left = [f for f in before if (folder / f).exists()]
                self.bus.emit("check.unmoved", {"files": left}, "code")
        return "\n\n".join(answers)
