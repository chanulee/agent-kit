"""옮긴 뒤 비어 버린 폴더 정리. 다른 파일이 남은 폴더, 실습 폴더 자체, .agentkit 은 그대로 둡니다."""
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
    (f / "학업/스케줄/plan.xlsx").write_text("x", encoding="utf-8")
    (f / "학업/스케줄/.DS_Store").write_text("x", encoding="utf-8")      # Mac이 몰래 만드는 파일은 빈 것으로 봄
    (f / "학업/notes.txt").write_text("x", encoding="utf-8")
    (f / "문서").mkdir()
    (f / "문서/a.pdf").write_text("x", encoding="utf-8")
    (f / "문서/b.pdf").write_text("x", encoding="utf-8")
    _approve_all(f, [{"src": "학업/스케줄/plan.xlsx", "dst": "수업/"}, {"src": "문서/a.pdf", "dst": "돈/"}])
    assert (f / "수업/plan.xlsx").exists() and (f / "돈/a.pdf").exists()
    assert not (f / "학업/스케줄").exists()            # 비어 버린 하위 폴더 정리
    assert (f / "학업/notes.txt").exists()              # 파일이 남은 폴더는 그대로
    assert (f / "문서/b.pdf").exists()
    assert (f / ".agentkit").exists() and f.exists()


def test_undo_restores_and_cleans_nested_rooms(tmp_path):
    f = tmp_path / "copy"
    f.mkdir()
    (f / "shot.png").write_text("x", encoding="utf-8")
    _approve_all(f, [{"src": "shot.png", "dst": "이미지/스크린샷/"}])
    assert (f / "이미지/스크린샷/shot.png").exists()
    move.undo_all()
    assert (f / "shot.png").exists()
    assert not (f / "이미지").exists()                   # 두 단계 빈 폴더 모두 정리


def test_windows_unsafe_names_are_fixed(tmp_path):
    """모델이 지어낸 이름에 Windows에서 못 쓰는 글자가 있어도 옮기기·노트 쓰기가 됩니다."""
    from tools import safe_name
    from tools.write import write_file
    assert safe_name('정리?: "최종"*') == "정리__ _최종__"
    assert safe_name("CON") == "_CON" and safe_name("노트. ") == "노트"
    f = tmp_path / "copy"
    f.mkdir()
    (f / "a.png").write_text("x", encoding="utf-8")
    out = _approve_all(f, [{"src": "a.png", "dst": "이미지?/레퍼런스*/"}])
    assert "1개를 옮겼습니다" in out and (f / "이미지_/레퍼런스_/a.png").exists()
    assert write_file("리서치/트렌드: 2024?.md", "# 노트").startswith("저장했습니다")
    assert (f / "리서치/트렌드_ 2024_.md").exists()
