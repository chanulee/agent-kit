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

import tools  # noqa: E402
from engine import core  # noqa: E402
from tools import move  # noqa: E402


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
    shutil.copy(REPO / "mcp.json", root / "mcp.json")
    monkeypatch.setattr(core, "ROOT", root)
    for k in core.KEYS:
        monkeypatch.delenv(k, raising=False)
    shutil.copytree(REPO / "sample_downloads", folder)
    tools.STATE["folder"] = folder
    tools.STATE["ids"] = {}
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


# ───────── 도구 ─────────

def test_find_handles_ids_nfd_typos_and_blocks_outside(kit):
    _, folder = kit
    (folder / unicodedata.normalize("NFD", "졸업 전시 포스터.png")).write_bytes(b"x")
    out = tools.TOOLS["list_files"]["func"]()
    assert "[1]" in out and "졸업 전시 포스터.png" in out           # 모델에는 항상 완성형(NFC) 이름
    assert tools.find("졸업 전시 포스터.png").exists()              # NFD로 저장된 파일도 찾음
    assert tools.find("1").exists()                                  # 번호로도 찾음
    assert tools.find("졸업 전시 포스타.png").exists()               # 작은 오타도 찾음
    for bad in ("../x", "/etc/passwd", "~/x", "../../copy/todo.md"):
        with pytest.raises(PermissionError):
            tools.find(bad)


def test_write_file_markdown_only_inside_copy(kit):
    _, folder = kit
    tools.load_all()
    out = tools.TOOLS["write_file"]["func"](path="리서치/노트.md", content="# 안녕\n")
    assert out.startswith("저장했습니다")
    assert (folder / "리서치/노트.md").read_text(encoding="utf-8").startswith("# 안녕")
    assert tools.TOOLS["write_file"]["func"](path="리서치/노트.md", content="# 또").startswith("error:")
    for bad in ("../x.md", "a.txt", "/tmp/x.md", "리서치/비밀.env"):
        assert tools.TOOLS["write_file"]["func"](path=bad, content="x").startswith("error:")


def test_plan_review_edit_reject_move_undo(kit):
    _, folder = kit
    tools.TOOLS["list_files"]["func"]()
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

def test_chat_without_tools(kit, monkeypatch):
    eng = engine_with([reply("안녕하세요!")], monkeypatch)
    assert eng.run("안녕") == "안녕하세요!"
    ev = kinds(eng.events())
    assert "model.send" in ev and "model.response" in ev and "tool.started" not in ev


def test_tool_error_does_not_stop_loop_and_knobs(kit, monkeypatch):
    root, _ = kit
    core.set_yaml(root / "agents/my-agent/agent.yaml", "tools", ["peek_file", "list_files", "get_time"])
    core.set_yaml(root / "agents/my-agent/agent.yaml", "max_turns", 4)
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
    eng = engine_with([reply("링크를 읽어 봤는데 접속이 안 돼요.")], monkeypatch)
    eng.run("이 링크 읽어 줘: https://nope.example")
    assert "warn.says_but_no_action" in kinds(eng.events())


def test_retry_is_visible(kit, monkeypatch):
    err = Exception("Error code: 429 - rate limit, retry in 10ms")
    eng = engine_with([err, reply("됐어요")], monkeypatch)
    assert eng.run("안녕") == "됐어요"
    w = [e for e in eng.events() if e["event_type"] == "retry.waiting"]
    assert w and w[0]["data"]["code"] == "429"


def test_move_needs_human_review(kit, monkeypatch):
    root, folder = kit
    core.set_yaml(root / "agents/my-agent/agent.yaml", "tools", ["propose_plan", "move_files", "list_files"])
    core.set_yaml(root / "agents/my-agent/agent.yaml", "skills", ["curator"])
    core.set_yaml(root / "agents/my-agent/agent.yaml", "ask_before", ["move_files"])

    def plan(_=None):
        return reply(calls=[("propose_plan", {"moves": [{"src": "todo.md", "dst": "문서/"}]})])

    def mv(_=None):
        p = json.loads((folder / ".agentkit/plan.json").read_text())
        return reply(calls=[("move_files", {"plan_id": p["plan_id"]})])
    eng = engine_with([reply(calls=[("load_skill", {"name": "curator"})]), plan(), mv, reply("정리했어요")], monkeypatch)

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


def test_skill_is_read_only_when_needed(kit, monkeypatch):
    """스킬은 처음엔 이름과 한 줄 설명만. 본문은 load_skill을 부를 때만 대화에 들어갑니다."""
    root, _ = kit
    core.set_yaml(root / "agents/my-agent/agent.yaml", "skills", ["curator"])
    seen = []
    eng = engine_with([lambda: seen.append("1") or reply(calls=[("load_skill", {"name": "curator"})]),
                       reply(calls=[("load_skill", {"name": "research-note"})]),   # 켜지 않은 스킬
                       reply("다 읽었어요")], monkeypatch)
    sent = []
    real = core._orig_create
    monkeypatch.setattr(core, "_orig_create", lambda self, model, messages, **kw: sent.append(messages) or real(self, model, messages, **kw))
    eng.run("정리 규칙이 뭐야?")
    system = sent[0][0]["content"]
    assert "- curator: 정리 스킬" in system and "## 전시실(폴더)" not in system      # 처음엔 목록만
    assert any("## 전시실(폴더)" in str(m) for m in sent[1])          # 읽은 뒤에는 본문이 대화에
    evs = eng.events()
    assert [e["data"]["skills"] for e in evs if e["event_type"] == "skill.loaded"] == [["curator"]]
    bad = [e for e in evs if e["event_type"] == "tool.completed" and "켜져 있지 않습니다" in json.dumps(e["data"], ensure_ascii=False)]
    assert bad


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
    assert s["agent"] == "my-agent"
    assert s["tools"]["web_search"]["ok"] is False and "mcp.json" in s["tools"]["web_search"]["why"]
    assert {x["name"] for x in s["skills"]} >= {"curator", "research-note"}
    c.post("/api/set", json={"target": "agent:my-agent", "key": "max_turns", "value": 3})
    text = (root / "agents/my-agent/agent.yaml").read_text(encoding="utf-8")
    assert "max_turns: 3" in text and "# ── 루프 조절 ──" in text          # 주석 유지
    pv = c.get("/api/folder/preview?kind=sample").json()["items"]
    assert any(i["skip"] for i in pv if i["name"].startswith("통장"))         # 민감 파일은 기본 제외
    keep = [i["name"] for i in pv if not i["skip"]]
    r = c.post("/api/folder/copy", json={"kind": "sample", "include": keep}).json()
    assert r["copied"] == len(keep) and not (folder / "통장사본_스캔.jpg").exists()
    assert c.post("/api/set", json={"target": "config", "key": "agent", "value": "docent"},
                  headers={"origin": "https://evil.com"}).status_code == 403
    turned = c.post("/api/mcp", json={"name": "tavily", "enabled": True, "agent": "my-agent"})
    assert turned.status_code == 200
    saved = json.loads((root / "mcp.json").read_text(encoding="utf-8"))
    assert saved["tavily"]["enabled"] is True
    assert "web_search" in (root / "agents/my-agent/agent.yaml").read_text(encoding="utf-8")


def test_write_file_approval_shows_preview(kit, monkeypatch):
    root, folder = kit
    core.set_yaml(root / "agents/my-agent/agent.yaml", "tools", ["write_file"])
    core.set_yaml(root / "agents/my-agent/agent.yaml", "ask_before", ["write_file"])
    content = "# 연구 노트\n\n한 줄 요약입니다."

    def call():
        return reply(calls=[("write_file", {"path": "리서치/노트.md", "content": content})])

    eng = engine_with([call(), reply("노트를 저장했어요")], monkeypatch)

    def human():
        while not eng.pending:
            time.sleep(0.02)
        aid, box = next(iter(eng.pending.items()))
        assert "연구 노트" in box["view"]["preview"]["content"]
        assert box["view"]["preview"]["path"] == "리서치/노트.md"
        eng.answer(aid, {"action": "approve"})
    threading.Thread(target=human, daemon=True).start()
    assert eng.run("노트 써 줘") == "노트를 저장했어요"
    assert (folder / "리서치/노트.md").read_text(encoding="utf-8") == content
    assert "approval.requested" in kinds(eng.events())


def test_team_run_shows_handoff(kit, monkeypatch):
    eng = engine_with([reply("디자인과 학생의 폴더로 보여요."), reply("갤러리 초안을 적었어요.")], monkeypatch)
    out = eng.run("정리해 줘", mode="team")
    evs = eng.events()
    ev = kinds(evs)
    assert ev.count("agent.start") == 2
    assert "team.start" in ev and "agent.handoff" in ev and "team.step" in ev
    hand = next(e for e in evs if e["event_type"] == "agent.handoff")
    assert "디자인과" in hand["data"]["passed"]
    assert "디자인과" in out and "갤러리" in out
    assert len([e for e in evs if e["event_type"] == "chat.reply"]) == 2


def test_step4_wrong_plan_id_and_reject_then_approve(kit, monkeypatch):
    """④: 모델이 plan_id를 잊어도 지금 계획으로 옮기고, 거절한 뒤 다시 부르면 계획을 새로 세우지 않고 같은 카드가 뜹니다."""
    root, folder = kit
    core.set_yaml(root / "agents/my-agent/agent.yaml", "tools", ["propose_plan", "move_files", "list_files"])
    core.set_yaml(root / "agents/my-agent/agent.yaml", "ask_before", ["move_files"])
    tools.STATE["folder"] = folder
    move.propose_plan([{"src": "todo.md", "dst": "문서/"}])                     # ③에서 세워 둔 계획
    eng = engine_with([reply(calls=[("move_files", {"plan_id": "p000000"})]),   # 틀린 번호
                       reply("알겠어요, 안 옮겼어요"),
                       reply(calls=[("move_files", {})]),                        # 번호 없이
                       reply("옮겼어요")], monkeypatch)
    answers = iter([{"action": "deny", "comment": "아직은 싫어"}, {"action": "submit", "items": {}}])
    cards = []

    def human():
        done = 0
        while done < 2:
            for aid, box in list(eng.pending.items()):
                cards.append(box["view"]["plan"]["plan_id"])
                eng.answer(aid, next(answers))
                done += 1
            time.sleep(0.02)
    threading.Thread(target=human, daemon=True).start()
    eng.run("계획대로 옮겨 줘")
    assert (folder / "todo.md").exists()                                         # 거절 → 안 옮김
    ev = kinds(eng.events())
    assert "loop.plan_id_fixed" in ev
    eng.run("이번엔 옮겨 줘")
    assert (folder / "문서/todo.md").exists()                                    # 같은 계획으로 옮김
    assert len(cards) == 2 and cards[0] == cards[1]                              # 새 계획 없이 같은 카드
