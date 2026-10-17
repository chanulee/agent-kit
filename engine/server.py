"""대시보드 서버 (내 노트북 안에서만 열림, 127.0.0.1)."""
import asyncio
import json
import os
import queue
import shutil
import sys
import threading
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse

from engine import core
from tools import move, nfc

ROOT = core.ROOT
SAMPLE = ROOT / "sample_downloads"
SENSITIVE = ["신분증", "여권", "주민", "통장", "계좌", "계약", "성적", "진단", "영수증", "passport", "bank", "password",
             "비밀번호", ".env", ".pem", ".key"]
AGENT_KEYS = {"agent", "team_partner", "tools", "max_turns", "limits", "no_repeat", "ask_before", "retry",
              "remember_tool_results", "skills"}


def source_folder(kind: str, path: str = "") -> Path:
    if kind == "sample":
        return SAMPLE
    if kind == "downloads":
        for c in (_windows_downloads(), Path.home() / "Downloads", Path.home() / "다운로드",
                  Path.home() / "OneDrive" / "Downloads"):
            if c and c.is_dir():
                return c
        raise HTTPException(400, "다운로드 폴더를 찾지 못했습니다. 폴더 경로를 직접 붙여 넣어 주세요.")
    p = Path(os.path.expanduser(path.strip().strip('"').strip("'")))
    if not p.is_dir():
        raise HTTPException(400, f"폴더가 없습니다: {p}  (Finder나 탐색기에서 폴더를 이 칸으로 끌어다 놓거나, "
                                 "탐색기 주소창의 경로를 복사해 붙여 넣으세요)")
    return p


def _windows_downloads() -> Path | None:
    """Windows는 다운로드 폴더를 OneDrive나 D: 드라이브로 옮겨 둔 경우가 많아서, 윈도우가 기억하는 실제 위치를 읽습니다."""
    if sys.platform != "win32":
        return None
    try:
        import winreg
        key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            raw, _ = winreg.QueryValueEx(k, "{374DE290-123F-4565-9164-39C4925E467B}")  # 다운로드 폴더 번호
        return Path(os.path.expandvars(raw))
    except OSError:
        return None


OS_FILES = {"desktop.ini", "thumbs.db", ".ds_store"}  # 운영체제가 만드는 숨은 파일


def preview(src: Path) -> list[dict]:
    items = []
    def mtime(x):
        try:
            return -x.stat().st_mtime
        except OSError:
            return 0
    for p in sorted(src.iterdir(), key=mtime):
        try:
            if not p.is_file() or p.name.startswith((".", "_dates")) or p.name.lower() in OS_FILES:
                continue
            p.stat()
        except OSError:  # Windows: 다른 프로그램이 잡고 있거나 OneDrive에만 있는 파일
            continue
        why = next((f"민감해 보이는 이름 '{w}'" for w in SENSITIVE if w in nfc(p.name).lower()), "")
        if p.stat().st_size > 20 * 1024 * 1024:
            why = why or "20MB보다 큼"
        items.append({"name": nfc(p.name), "kb": p.stat().st_size // 1024, "skip": why})
    return items


def skill_catalog() -> list[dict]:
    out = []
    root = ROOT / "skills"
    if not root.is_dir():
        return out
    for d in sorted(root.iterdir()):
        md = d / "SKILL.md"
        if md.is_file():
            first = md.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
            out.append({"name": d.name, "title": first or d.name})
    return out


def state() -> dict:
    cfg = core.config()
    agents = {}
    for d in sorted((ROOT / "agents").iterdir()):
        if (d / "agent.yaml").exists():
            try:
                a = core.load_agent(d.name)
                agents[d.name] = {k: a[k] for k in ("title", "tools", "max_turns", "limits", "no_repeat", "ask_before",
                                                    "retry", "remember_tool_results", "skills")}
                agents[d.name]["prepared"] = d.name != cfg["agent"]
            except Exception as e:  # noqa: BLE001
                agents[d.name] = {"title": d.name, "error": f"agent.yaml 오류: {e}"}
    f = cfg["folder_path"]
    mcp = {}
    for name, raw in core.load_mcp().items():
        if isinstance(raw, dict):
            mcp[name] = {"enabled": bool(raw.get("enabled")), "tools": list(raw.get("tools") or []),
                         "note": raw.get("note") or ""}
    return {"agent": cfg["agent"], "team_partner": cfg.get("team_partner") or "docent",
            "model": cfg.get("model"), "agents": agents, "tools": core.tool_status(), "skills": skill_catalog(),
            "mcp": mcp,
            "keys": {"model": bool(os.environ.get(cfg.get("key_env", "ZAI_API_KEY"))),
                     "web": bool(os.environ.get("TAVILY_API_KEY"))},
            "folder": {"path": str(f), "ok": f.is_dir(),
                       "files": sum(1 for p in f.rglob("*") if p.is_file() and ".agentkit" not in p.parts) if f.is_dir() else 0,
                       "gallery": (f / "gallery.html").exists()}}


def create_app(engine: core.Engine | None = None) -> FastAPI:
    eng = engine or core.Engine()
    app = FastAPI(docs_url=None, redoc_url=None)
    app.state.engine = eng
    stamps = {}

    def watch():  # 파일을 직접 고쳐도 화면이 따라오게 (3초 안)
        while True:
            files = [ROOT / "config.yaml", ROOT / "mcp.json",
                     *ROOT.glob("agents/*/agent.yaml"), *ROOT.glob("agents/*/persona.md"),
                     *ROOT.glob("tools/*.py"), *ROOT.glob("skills/*/SKILL.md")]
            now = {str(p): p.stat().st_mtime for p in files if p.exists()}
            if stamps and now != stamps.get("v"):
                eng.bus.emit("state", safe_state())
            stamps["v"] = now
            threading.Event().wait(1.5)

    def safe_state():
        try:
            return {**state(), "busy": eng.busy.locked()}
        except Exception as e:  # noqa: BLE001
            return {"error": f"설정 파일을 읽을 수 없습니다: {e}. 들여쓰기·콜론(:)을 확인하세요."}

    threading.Thread(target=watch, daemon=True).start()

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method == "POST" and origin and not origin.startswith(("http://127.0.0.1", "http://localhost")):
            return JSONResponse({"detail": "다른 사이트에서 온 요청은 받지 않습니다."}, status_code=403)
        return await call_next(request)

    @app.get("/", response_class=HTMLResponse)
    def index():
        return (Path(__file__).parent / "dashboard.html").read_text(encoding="utf-8")

    @app.get("/api/state")
    def get_state():
        return safe_state()

    @app.post("/api/set")
    async def set_value(req: Request):
        """화면 버튼 → 파일 한 줄. target: config | agent:<이름>"""
        b = await req.json()
        target, key, value = b.get("target", "config"), b["key"], b.get("value")
        path = ROOT / "config.yaml" if target == "config" else ROOT / "agents" / target.split(":", 1)[1] / "agent.yaml"
        allowed = {"agent", "team_partner"} if target == "config" else AGENT_KEYS
        if key not in allowed:
            raise HTTPException(400, f"바꿀 수 없는 값: {key}")
        core.set_yaml(path, key, value)
        if target.startswith("agent:"):
            eng.history.pop(target.split(":", 1)[1], None)
        s = safe_state()
        eng.bus.emit("state", s)
        return {"file": str(path.relative_to(ROOT)), "state": s}

    @app.post("/api/mcp")
    async def set_mcp(req: Request):
        """mcp.json 의 켜짐 스위치. 켜면 그 서버의 도구를 에이전트 목록에 넣고, 끄면 뺍니다."""
        b = await req.json()
        name = b.get("name") or "tavily"
        enabled = bool(b.get("enabled"))
        path = ROOT / "mcp.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise HTTPException(400, f"mcp.json을 읽을 수 없습니다: {e}")
        if name not in data or not isinstance(data[name], dict):
            raise HTTPException(404, "mcp.json에 없는 이름입니다")
        data[name]["enabled"] = enabled
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        agent = b.get("agent") or core.config()["agent"]
        ypath = ROOT / "agents" / agent / "agent.yaml"
        extra = [t for t in (data[name].get("tools") or []) if isinstance(t, str)]
        if ypath.exists() and extra:
            current = list(core.read_yaml(ypath).get("tools") or [])
            if enabled:
                for t in extra:
                    if t not in current:
                        current.append(t)
            else:
                current = [t for t in current if t not in extra]
            core.set_yaml(ypath, "tools", current)
            eng.history.pop(agent, None)
        s = safe_state()
        eng.bus.emit("state", s)
        return {"file": "mcp.json", "state": s}

    @app.get("/api/file")
    def show_file(path: str):
        p = (ROOT / path).resolve()
        if ROOT not in p.parents or p.suffix not in (".yaml", ".md", ".py", ".html", ".json") or ".env" in p.name:
            raise HTTPException(404)
        return {"path": path, "text": p.read_text(encoding="utf-8")}

    @app.post("/api/chat")
    async def chat(req: Request):
        text = ((await req.json()).get("text") or "").strip()
        if not text:
            raise HTTPException(400, "메시지가 비어 있습니다")
        if eng.busy.locked():
            raise HTTPException(409, "아직 이전 질문을 처리 중입니다. 끝나거나 [멈춤]을 누른 뒤 보내세요.")
        threading.Thread(target=eng.run, args=(text,), daemon=True).start()
        return {"ok": True}

    @app.post("/api/team")
    async def team(req: Request):
        body = await req.json()
        text = (body.get("text") or "").strip() or "이 폴더를 정리하고, 어울리는 작품으로 갤러리를 만들어 줘."
        if eng.busy.locked():
            raise HTTPException(409, "아직 이전 질문을 처리 중입니다. 끝나거나 [멈춤]을 누른 뒤 보내세요.")
        threading.Thread(target=eng.run, args=(text,), kwargs={"mode": "team"}, daemon=True).start()
        return {"ok": True}

    @app.post("/api/stop")
    def stop():
        eng.cancel.set()
        return {"ok": True}

    @app.post("/api/new_chat")
    def new_chat():
        eng.history.clear()
        return {"ok": True}

    @app.post("/api/approve/{aid}")
    async def approve(aid: str, req: Request):
        if not eng.answer(aid, await req.json()):
            raise HTTPException(404, "이미 처리된 승인입니다")
        return {"ok": True}

    @app.get("/api/folder/preview")
    def folder_preview(kind: str = "sample", path: str = ""):
        src = source_folder(kind, path)
        return {"source": str(src), "items": preview(src)}

    @app.post("/api/folder/copy")
    async def folder_copy(req: Request):
        """고른 폴더를 사본으로 복사합니다. 원본은 건드리지 않고, 예전 사본은 지우지 않고 옆으로 옮깁니다."""
        b = await req.json()
        src = source_folder(b.get("kind", "sample"), b.get("path", ""))
        dest = core.config()["folder_path"]
        if dest.resolve() == src.resolve() or src.resolve() in dest.resolve().parents:
            raise HTTPException(400, "사본 폴더가 원본 안에 있으면 안 됩니다.")
        if dest.exists() and any(dest.iterdir()):
            old = dest.parent / "old" / datetime.now().strftime("%Y%m%d-%H%M%S")
            old.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dest), str(old))
        dest.mkdir(parents=True, exist_ok=True)
        dates = json.loads((SAMPLE / "_dates.json").read_text(encoding="utf-8")) if src == SAMPLE else {}
        chosen = set(b.get("include") or [])
        n, skipped = 0, []
        for p in src.iterdir():
            if p.is_file() and nfc(p.name) in chosen and n < 60:
                try:
                    shutil.copy2(p, dest / nfc(p.name))
                except OSError as e:  # Windows: 내려받는 중, 다른 프로그램이 열어 둠, OneDrive에만 있음 → 건너뜀
                    skipped.append(f"{nfc(p.name)} ({type(e).__name__})")
                    continue
                if p.name in dates:
                    t = datetime.fromisoformat(dates[p.name]).timestamp()
                    os.utime(dest / nfc(p.name), (t, t))
                n += 1
        eng.history.clear()
        eng.bus.emit("state", safe_state())
        return {"copied": n, "dest": str(dest), "skipped": skipped}

    @app.post("/api/undo")
    def undo():
        import tools
        tools.STATE["folder"] = core.config()["folder_path"]
        return {"moves": move.undo_all()}

    @app.get("/gallery")
    def gallery():
        p = core.config()["folder_path"] / "gallery.html"
        if not p.exists():
            return HTMLResponse("<p style='font:18px sans-serif;padding:40px'>아직 갤러리가 없습니다. 위쪽 [팀 실행]을 눌러 보세요.</p>")
        return FileResponse(p)

    @app.get("/api/events")
    async def events(request: Request):
        q: queue.Queue = queue.Queue()
        eng.bus.subs.append(q)

        async def stream():
            try:
                yield f"data: {json.dumps({'event_type': 'state', 'data': safe_state()}, ensure_ascii=False)}\n\n"
                for aid, box in list(eng.pending.items()):  # 새로고침해도 승인 카드가 다시 뜸
                    yield f"data: {json.dumps({'event_type': 'approval.requested', 'agent': '', 'data': {'id': aid, **box['view']}}, ensure_ascii=False)}\n\n"
                while not await request.is_disconnected():
                    try:
                        ev = await asyncio.to_thread(q.get, True, 1.0)
                        yield f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"
                    except queue.Empty:
                        yield ": ping\n\n"
            finally:
                eng.bus.subs.remove(q)
        return StreamingResponse(stream(), media_type="text/event-stream")

    return app
