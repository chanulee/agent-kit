"""옮기기 도구: 계획표 → 사람 심사(✅❌✏️💬) → 승인된 것만 한 번에 옮기기 → 되돌리기.

- propose_plan 은 계획표(plan.json)만 씁니다. 파일은 그대로입니다.
- move_files 는 agent.yaml 의 ask_before 에 있으면 사람 심사를 거칩니다(엔진이 화면 카드를 띄움).
- 덮어쓰지 않고(_2, _3), 지우지 않고, 모든 이동은 undo.json 에 남습니다.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from tools import find, folder, nfc, tool


class Move(BaseModel):
    src: str = Field(description="file ID number from list_files (e.g. '3') or its exact path")
    dst: str = Field(description="destination folder like '이미지/', or '이미지/new_name.png' to rename")
    reason: str = Field(default="", description="short Korean reason")


def _meta() -> Path:
    d = folder() / ".agentkit"
    d.mkdir(exist_ok=True)
    return d


def _load(name, default):
    try:
        return json.loads((_meta() / name).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return default


def _save(name, data):
    (_meta() / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _clean_dst(dst: str) -> str:
    dst = nfc(str(dst).strip().replace("\\", "/")).strip("/")
    if not dst or dst.startswith("~") or ".." in dst.split("/") or ":" in dst or dst.startswith(".agentkit"):
        raise PermissionError(f"사본 폴더 밖이나 잘못된 경로입니다: {dst}")
    return dst


@tool("📝", group="정리")
def propose_plan(moves: list[Move]) -> str:
    """Save a move/rename plan for the user to review. Does NOT move anything. Then call move_files(plan_id).

    Args:
        moves: one entry per file to move or rename
    """
    old = _load("plan.json", {})
    again = old.get("status") == "reviewing"           # 사람이 고친 뒤 다시 짜는 중(v2, v3 …)
    locked, rejected = (old.get("locked", {}), old.get("rejected", [])) if again else ({}, [])
    prev = {i["src"]: i["dst"] for i in old.get("items", [])} if again else {}
    items, problems = [], []
    for m in moves:
        m = m if isinstance(m, Move) else Move(**m)
        try:
            src = nfc(find(m.src).relative_to(folder()).as_posix())
            dst = m.dst if not (m.dst.endswith("/") or "." not in Path(m.dst).name) else f"{m.dst.rstrip('/')}/{Path(src).name}"
            dst = locked.get(src) or _clean_dst(dst)  # 사람이 고친 값은 엔진이 지킵니다
        except (PermissionError, FileNotFoundError) as e:
            problems.append(str(e))
            continue
        status = "rejected" if src in rejected else "edited" if src in locked else "pending"
        items.append({"id": len(items) + 1, "src": src, "dst": dst, "reason": m.reason, "status": status,
                      "changed": bool(prev) and prev.get(src) != dst})
    if not items:
        return "error: 계획에 쓸 수 있는 항목이 없습니다. " + " / ".join(problems)
    plan = {"plan_id": old["plan_id"] if again else datetime.now().strftime("p%H%M%S"),
            "version": old.get("version", 0) + 1 if again else 1, "status": "reviewing",
            "items": items, "locked": locked, "rejected": rejected, "notes": old.get("notes", []) if again else []}
    _save("plan.json", plan)
    msg = f"계획 v{plan['version']} 저장(plan_id={plan['plan_id']}, {len(items)}개). 아직 옮기지 않았습니다. " \
          f"이제 move_files(plan_id=\"{plan['plan_id']}\")를 부르세요. 사용자가 화면에서 심사합니다."
    return msg + ("\n빠진 항목: " + " / ".join(problems) if problems else "")


@tool("📦", group="정리")
def move_files(plan_id: str = "") -> str:
    """Move the files in the current plan (the one saved by propose_plan). Only items the user approved are moved,
    all at once. Never deletes. If the user says "move as planned", just call this; no need to plan again.

    Args:
        plan_id: optional. plan_id from propose_plan; if missing or wrong, the current plan is used
    """
    plan = current_plan()
    if not plan:
        return "error: 심사 중인 계획이 없습니다. propose_plan으로 계획을 먼저 세우세요."
    plan_id = plan["plan_id"]  # 계획 파일은 하나뿐입니다. 번호를 잃어버려도 지금 계획을 씁니다.
    undo = _load("undo.json", {"moves": []})
    moved, skipped = [], []
    for it in plan["items"]:
        if it["status"] == "rejected":
            skipped.append(it["src"])
            continue
        try:
            src = find(it["src"])
            dst = folder() / _clean_dst(it["dst"])
            if dst.resolve() == src.resolve():  # 이미 그 자리에 있음 → 옮기지 않음
                skipped.append(f"{it['src']} (이미 그 자리)")
                continue
            n = 2
            while dst.exists():  # 덮어쓰기 금지
                dst = dst.with_name(f"{Path(it['dst']).stem}_{n}{dst.suffix}")
                n += 1
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
        except (PermissionError, FileNotFoundError, OSError) as e:
            skipped.append(f"{it['src']} ({e})")
            continue
        final = nfc(dst.relative_to(folder()).as_posix())
        undo["moves"].append({"from": it["src"], "to": final})
        moved.append(f"{it['src']} → {final}")
    plan["status"] = "done"
    _save("plan.json", plan)
    _save("undo.json", undo)
    out = f"{len(moved)}개를 옮겼습니다(지운 파일 없음, 되돌리기 가능).\n" + "\n".join(moved)
    if skipped:
        out += "\n옮기지 않음: " + ", ".join(skipped) + "\n거절한 것과 비슷한 파일도 앞으로 뺄지 사용자에게 물어보세요."
    if plan.get("notes"):
        out += "\n사용자가 알려 준 규칙: " + " / ".join(plan["notes"]) + " → SKILL.md에 적어 두자고 제안하세요."
    return out


# ---------------- 엔진이 쓰는 함수 (모델에게 보이는 도구는 아님) ----------------

def current_plan() -> dict | None:
    """지금 심사 중인 계획. 계획 파일(plan.json)은 하나뿐이라 번호 없이도 찾을 수 있습니다."""
    plan = _load("plan.json", {})
    return plan if plan.get("status") == "reviewing" else None


def review_card(plan_id: str = "") -> dict | None:
    """모델이 준 plan_id가 틀리거나 없어도 지금 심사 중인 계획을 돌려줍니다.
    (대화 기록에는 최종 답만 남아서, 앞 질문에서 받은 plan_id를 모델이 잊어버리기 때문)"""
    return current_plan()


def apply_review(plan_id: str, decision: dict) -> tuple[bool, str]:
    """사람의 심사 결과를 계획에 적습니다. (실행해도 되나, 모델에게 줄 말)"""
    plan = current_plan()
    if not plan:
        return False, "계획을 찾을 수 없습니다. propose_plan을 다시 부르세요."
    if decision.get("action") == "deny":
        # 거절 = "이번에는 옮기지 않음". 계획은 그대로 남겨서, 다음에 다시 move_files를 부르면 같은 카드가 뜹니다.
        plan.setdefault("notes", [])
        c = (decision.get("comment") or "").strip()
        if c:
            plan["notes"].append(c)
        _save("plan.json", plan)
        return False, ("사용자가 이번에는 옮기지 않기로 했습니다. 아무 파일도 옮기지 않았습니다. 계획은 그대로 남아 있습니다"
                       + (f". 사용자의 말: \"{c}\"" if c else "") + ". 무엇을 바꾸고 싶은지 물어보세요. "
                       "사용자가 다시 옮기라고 하면 계획을 새로 세우지 말고 move_files를 바로 부르세요.")
    choices = {str(k): v for k, v in (decision.get("items") or {}).items()}
    edits, comment = [], (decision.get("comment") or "").strip()
    for it in plan["items"]:
        c = choices.get(str(it["id"]), {})
        if c.get("action") == "reject":
            it["status"] = "rejected"
            plan["rejected"] = sorted(set(plan["rejected"]) | {it["src"]})
        elif c.get("action") == "edit" and c.get("dst"):
            try:
                it["dst"] = plan["locked"][it["src"]] = _clean_dst(c["dst"])
            except PermissionError as e:
                return False, str(e)
            it["status"] = "edited"
            edits.append(f"{it['src']} → {it['dst']}")
        elif it["status"] != "rejected":
            it["status"] = "approved"
    if comment:
        plan["notes"].append(comment)
    plan["notes"] += [f"수정 예: {e}" for e in edits]
    _save("plan.json", plan)
    if edits or comment:
        return False, ("사용자가 계획을 고쳤습니다(아직 안 옮김). " + (f"수정: {'; '.join(edits)}. " if edits else "")
                       + (f"한마디: \"{comment}\". " if comment else "")
                       + "고친 값은 그대로 두고, 같은 패턴을 비슷한 파일에만 적용해 propose_plan으로 새 버전을 만든 뒤 move_files를 다시 부르세요.")
    return True, "승인"


def undo_all() -> list[str]:
    undo, done = _load("undo.json", {"moves": []}), []
    for mv in reversed(undo["moves"]):
        if mv.get("undone"):
            continue
        try:
            cur, back = find(mv["to"]), folder() / mv["from"]
            if back.exists():
                back = back.with_name(f"{back.stem}_되돌림{back.suffix}")
            back.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(cur), str(back))
            mv["undone"] = True
            done.append(f"{mv['to']} → {mv['from']}")
            if not any(cur.parent.iterdir()) and cur.parent != folder():
                cur.parent.rmdir()  # 비어 버린 전시실 폴더만 정리
        except (FileNotFoundError, PermissionError, OSError) as e:
            done.append(f"되돌리지 못함: {mv['to']} ({e})")
    _save("undo.json", undo)
    return done
