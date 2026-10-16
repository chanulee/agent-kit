"""키 없이 도는 시험: aisuite Client·Runner는 진짜를 쓰고, 모델 서버에 보내는 부분만 대본으로 바꿉니다.
실행:  uv run pytest
"""
import json
import shutil
import sys
import threading
import time
import unicodedata
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import aisuite as ai  # noqa: E402
from openai.types.chat import ChatCompletion  # noqa: E402

import hands  # noqa: E402
from engine import core  # noqa: E402
from hands import move  # noqa: E402


def reply(text=None, calls=()):
    tc = [{"id": f"c{i}{time.time_ns()}", "type": "function",
           "function": {"name": n, "arguments": json.dumps(a, ensure_ascii=False)}} for i, (n, a) in enumerate(calls)]
    return ChatCompletion.model_validate({
        "id": "x", "object": "chat.completion", "created": 0, "model": "fake",
        "choices": [{"index": 0, "finish_reason": "tool_calls" if tc else "stop",
                     "message": {"role": "assistant", "content": text, "tool_calls": tc or None}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}})


@pytest.fixture
def kit(tmp_path, monkeypatch):
    root = tmp_path / "kit"
    for d in ("agents", "skills", "sample_downloads"):
        shutil.copytree(REPO / d, root / d)
    folder = tmp_path / "copy"
    (root / "config.yaml").write_text((REPO / "config.yaml").read_text(encoding="utf-8")
                                      .replace("~/agent-workshop/copy", folder.as_posix()), encoding="utf-8")
    monkeypatch.setattr(core, "ROOT", root)
    for k in core.KEYS:
        monkeypatch.delenv(k, raising=False)
    shutil.copytree(REPO / "sample_downloads", folder)
    hands.STATE["folder"] = folder
    hands.STATE["ids"] = {}
    return root, folder


def engine_with(script, monkeypatch):
    """script: 모델이 차례로 돌려줄 답(또는 던질 예외) 목록."""
    script = list(script)

    def fake(self, model, messages, **kw):
        step = script.pop(0) if script else reply("(대본 끝)")
        if callable(step):           # 앞 결과를 보고 답을 만들어야 할 때
            step = step()
        if isinstance(step, Exception):
            raise step
        return step
    monkeypatch.setattr(core, "_orig_create", fake)
    eng = core.Engine(client=ai.Client({"openai": {"api_key": "test", "base_url": "http://fake"}}))
    seen = []
    q = __import__("queue").Queue()
    eng.bus.subs.append(q)
    eng.events = lambda: [q.get_nowait() for _ in range(q.qsize())] if True else seen
    return eng


def kinds(evs):
    return [e["event_type"] for e in evs]


# ───────── 손 ─────────

def test_find_handles_ids_nfd_typos_and_blocks_outside(kit):
    _, folder = kit
    (folder / unicodedata.normalize("NFD", "졸업 전시 포스터.png")).write_bytes(b"x")
    out = hands.HANDS["list_files"]["func"]()
    assert "[1]" in out and "졸업 전시 포스터.png" in out           # 모델에는 항상 완성형(NFC) 이름
    assert hands.find("졸업 전시 포스터.png").exists()              # NFD로 저장된 파일도 찾음
    assert hands.find("1").exists()                                  # 번호로도 찾음
    assert hands.find("졸업 전시 포스타.png").exists()               # 작은 오타도 찾음
    for bad in ("../x", "/etc/passwd", "~/x", "../../copy/todo.md"):
        with pytest.raises(PermissionError):
            hands.find(bad)


def test_plan_review_edit_reject_move_undo(kit):
    _, folder = kit
    hands.HANDS["list_files"]["func"]()
    msg = move.propose_plan([{"src": "todo.md", "dst": "문서/"}, {"src": "IMG_2031.jpg", "dst": "사진/"},
                             {"src": "cat_meme.gif", "dst": "사진/"}])
    pid = msg.split("plan_id=")[1].split(",")[0]
    assert (folder / "todo.md").exists()                              # 계획만, 아직 안 옮김
    ok, why = move.apply_review(pid, {"action": "submit", "items": {"1": {"action": "edit", "dst": "할일/todo.md"},
                                                                     "3": {"action": "reject"}}})
    assert not ok and "새 버전" in why
    move.propose_plan([{"src": "todo.md", "dst": "문서/"}, {"src": "IMG_2031.jpg", "dst": "사진/"},
                       {"src": "cat_meme.gif", "dst": "사진/"}])     # 모델이 수정을 무시해도
    plan = move.review_card(pid)
    assert plan["version"] == 2 and plan["items"][0]["dst"] == "할일/todo.md"   # 엔진이 사람 수정을 지킴
    assert move.apply_review(pid, {"action": "submit", "items": {}})[0]
    (folder / "사진").mkdir()
    (folder / "사진/IMG_2031.jpg").write_text("먼저 있던 파일")
    out = move.move_files(pid)
    assert "2개를 옮겼습니다" in out and (folder / "cat_meme.gif").exists()
    assert (folder / "사진/IMG_2031.jpg").read_text() == "먼저 있던 파일"        # 덮어쓰지 않음
    assert (folder / "사진/IMG_2031_2.jpg").exists()
    assert len(move.undo_all()) == 2 and (folder / "todo.md").exists()


# ───────── 루프 (aisuite Runner + 우리 손잡이) ─────────

def test_L1_chat(kit, monkeypatch):
    eng = engine_with([reply("안녕하세요!")], monkeypatch)
    assert eng.run("안녕") == "안녕하세요!"
    ev = kinds(eng.events())
    assert "model.send" in ev and "model.response" in ev and "tool.started" not in ev


def test_L3_tool_error_does_not_stop_loop_and_knobs(kit, monkeypatch):
    root, _ = kit
    core.set_yaml(root / "config.yaml", "level", "L3")
    core.set_yaml(root / "agents/detective/agent.yaml", "max_turns", 4)
    eng = engine_with([reply(calls=[("peek_file", {"path": "없는파일.txt"})]),     # 손 오류 → 글로
                       reply(calls=[("list_files", {})]),
                       reply(calls=[("list_files", {})]),                            # 같은 호출 → 막힘
                       reply(calls=[("get_time", {})])], monkeypatch)                # 4턴째에도 손 → 턴 한도
    eng.run("폴더 주인은?")
    evs = eng.events()
    ev = kinds(evs)
    assert "run.failed" not in ev and "error.card" not in ev
    first = next(e for e in evs if e["event_type"] == "tool.completed")
    assert "error" in json.dumps(first["data"], ensure_ascii=False)
    assert "loop.repeat_blocked" in ev and "run.max_turns" in ev


def test_says_but_no_action_warning(kit, monkeypatch):
    root, _ = kit
    core.set_yaml(root / "config.yaml", "level", "L3")
    eng = engine_with([reply("링크를 읽어 봤는데 접속이 안 돼요.")], monkeypatch)
    eng.run("이 링크 읽어 줘: https://nope.example")
    assert "warn.says_but_no_action" in kinds(eng.events())


def test_retry_is_visible(kit, monkeypatch):
    err = Exception("Error code: 429 - rate limit, retry in 10ms")
    eng = engine_with([err, reply("됐어요")], monkeypatch)
    assert eng.run("안녕") == "됐어요"
    w = [e for e in eng.events() if e["event_type"] == "retry.waiting"]
    assert w and w[0]["data"]["code"] == "429"


def test_curator_needs_human_review(kit, monkeypatch):
    root, folder = kit
    core.set_yaml(root / "config.yaml", "level", "L3")
    core.set_yaml(root / "config.yaml", "agent", "curator")

    def plan(_=None):
        return reply(calls=[("propose_plan", {"moves": [{"src": "todo.md", "dst": "문서/"}]})])

    def mv(_=None):
        p = json.loads((folder / ".agentkit/plan.json").read_text())
        return reply(calls=[("move_files", {"plan_id": p["plan_id"]})])
    eng = engine_with([plan(), mv, reply("정리했어요")], monkeypatch)

    def human():
        while not eng.pending:
            time.sleep(0.02)
        aid = next(iter(eng.pending))
        eng.answer(aid, {"action": "submit", "items": {}})
    threading.Thread(target=human, daemon=True).start()
    assert eng.run("전시실로 정리해 줘") == "정리했어요"
    assert (folder / "문서/todo.md").exists()
    ev = kinds(eng.events())
    assert "approval.requested" in ev and "approval.resolved" in ev and "skill.loaded" in ev


def test_missing_key_is_a_clear_card(kit, monkeypatch):
    eng = core.Engine()
    out = eng.run("안녕")
    assert "[준비]" in out and ".env" in out


def test_dashboard_toggle_writes_file_and_folder_copy(kit, monkeypatch):
    from fastapi.testclient import TestClient
    from engine import server
    root, folder = kit
    monkeypatch.setattr(server, "ROOT", root)
    monkeypatch.setattr(server, "SAMPLE", root / "sample_downloads")
    c = TestClient(server.create_app(core.Engine()))
    s = c.get("/api/state").json()
    assert s["hands"]["web_search"]["ok"] is False and "TAVILY" in s["hands"]["web_search"]["why"]
    c.post("/api/set", json={"target": "agent:detective", "key": "max_turns", "value": 3})
    text = (root / "agents/detective/agent.yaml").read_text(encoding="utf-8")
    assert "max_turns: 3" in text and "# ── 루프 손잡이 ──" in text          # 주석 유지
    pv = c.get("/api/folder/preview?kind=sample").json()["items"]
    assert any(i["skip"] for i in pv if i["name"].startswith("통장"))         # 민감 파일은 기본 제외
    keep = [i["name"] for i in pv if not i["skip"]]
    r = c.post("/api/folder/copy", json={"kind": "sample", "include": keep}).json()
    assert r["copied"] == len(keep) and not (folder / "통장사본_스캔.jpg").exists()
    assert c.post("/api/set", json={"key": "level", "value": "L2"}, headers={"origin": "https://evil.com"}).status_code == 403
