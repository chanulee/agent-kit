"""옮긴 뒤 비어 버린 폴더 정리. 다른 파일이 남은 폴더, 사본 폴더 자체, .agentkit 은 그대로 둡니다."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tools  # noqa: E402
from tools import move  # noqa: E402


def _approve_all(folder, moves):
    tools.STATE["folder"] = folder
    move.propose_plan(moves)
    assert move.apply_review("", {"action": "submit", "items": {}})[0]
    return move.move_files()


def test_emptied_folders_are_removed_but_others_stay(tmp_path):
    f = tmp_path / "copy"
    (f / "학업/스케줄").mkdir(parents=True)
    (f / "학업/스케줄/plan.xlsx").write_text("x")
    (f / "학업/스케줄/.DS_Store").write_text("x")      # Mac이 몰래 만드는 파일은 빈 것으로 봄
    (f / "학업/notes.txt").write_text("x")
    (f / "문서").mkdir()
    (f / "문서/a.pdf").write_text("x")
    (f / "문서/b.pdf").write_text("x")
    _approve_all(f, [{"src": "학업/스케줄/plan.xlsx", "dst": "수업/"}, {"src": "문서/a.pdf", "dst": "돈/"}])
    assert (f / "수업/plan.xlsx").exists() and (f / "돈/a.pdf").exists()
    assert not (f / "학업/스케줄").exists()            # 비어 버린 하위 폴더 정리
    assert (f / "학업/notes.txt").exists()              # 파일이 남은 폴더는 그대로
    assert (f / "문서/b.pdf").exists()
    assert (f / ".agentkit").exists() and f.exists()


def test_undo_restores_and_cleans_nested_rooms(tmp_path):
    f = tmp_path / "copy"
    f.mkdir()
    (f / "shot.png").write_text("x")
    _approve_all(f, [{"src": "shot.png", "dst": "이미지/스크린샷/"}])
    assert (f / "이미지/스크린샷/shot.png").exists()
    move.undo_all()
    assert (f / "shot.png").exists()
    assert not (f / "이미지").exists()                   # 두 단계 빈 폴더 모두 정리
