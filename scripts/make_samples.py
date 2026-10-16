"""샘플 다운로드 폴더(sample_downloads/)를 다시 만듭니다. 가상의 디자인 전공생 다운로드 40개.

이름과 내용은 모두 지어낸 것입니다. 실행: uv run scripts/make_samples.py
git은 파일 날짜를 지키지 않으므로, 날짜는 _dates.json에 적어 두고 사본을 만들 때 입힙니다.
"""
import json
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sample_downloads"

# (이름, 종류, 며칠 전, 내용/색)
FILES = [
    ("Screenshot 2026-10-01 at 3.12.44 PM.png", "img", 16, (230, 230, 240)),
    ("Screenshot 2026-10-03 at 11.02.10 AM.png", "img", 14, (210, 225, 250)),
    ("Screenshot 2026-10-09 at 1.47.31 AM.png", "img", 8, (40, 40, 60)),
    ("스크린샷 2026-10-12 오후 2.33.05.png", "img", 5, (250, 240, 220)),
    ("KakaoTalk_20261005_224512345.jpg", "img", 12, (255, 230, 0)),
    ("IMG_2031.jpg", "img", 40, (120, 160, 120)),
    ("IMG_2032.jpg", "img", 40, (110, 150, 200)),
    ("moodboard_ref_blue.png", "img", 22, (40, 90, 200)),
    ("moodboard_ref_blue (1).png", "img", 22, (40, 90, 200)),
    ("졸전_포스터_최종.png", "img", 3, (220, 60, 60)),
    ("졸전_포스터_최종_진짜최종.png", "img", 2, (230, 70, 50)),
    ("졸전_포스터_최종_진짜최종_수정.png", "img", 1, (240, 80, 40)),
    ("pinterest_typography_poster.jpg", "img", 30, (20, 20, 20)),
    ("logo_sketch_v2.png", "img", 25, (255, 255, 255)),
    ("cat_meme.gif", "gif", 60, (200, 170, 140)),
    ("과제3_최종.pdf", "pdf", 20, "Typography Studio - Assignment 3\nGrid systems and Korean type\nFinal version"),
    ("과제3_최종_진짜최종.pdf", "pdf", 19, "Typography Studio - Assignment 3\nGrid systems and Korean type\nREALLY final version"),
    ("invoice_oct.pdf", "pdf", 10, "INVOICE #2026-1007\nAdobe Creative Cloud - Student plan\nTotal: 23,100 KRW"),
    ("portfolio_2026_draft.pdf", "pdf", 6, "PORTFOLIO 2026\nGraphic Design / Branding / Editorial\nDraft - do not share"),
    ("color_theory_lecture5.pdf", "pdf", 35, "Lecture 5: Color Theory\nJosef Albers - Interaction of Color\nSimultaneous contrast"),
    ("museum_ticket_MMCA.pdf", "pdf", 45, "MMCA Seoul\nAdmission ticket\nExhibition: Korean Modern Art"),
    ("lecture5_notes.txt", "txt", 34, "색채학 5주차 노트\n- 알버스: 색은 혼자 있지 않다\n- 동시 대비 실습: 회색 사각형 두 개\n- 과제: 같은 색이 달라 보이는 포스터 1장"),
    ("졸전_아이디어_메모.txt", "txt", 9, "졸업 전시 아이디어\n1. 다운로드 폴더를 전시회로?\n2. 버려진 스크린샷 아카이브\n3. 폰트 수집가의 방"),
    ("todo.md", "txt", 4, "# 이번 주 할 일\n- [ ] 포스터 최종 (진짜)\n- [ ] 폰트 라이선스 확인\n- [x] 교수님 메일 답장"),
    ("interview_questions.txt", "txt", 13, "디자인 스튜디오 인턴 면접 질문 정리\n- 좋아하는 디자이너는?\n- 포트폴리오에서 제일 자신 있는 작업은?"),
    ("resume(1).docx", "bin", 28, b"PK fake docx"),
    ("font-Pretendard.zip", "zip", 50, "Pretendard-Regular.otf"),
    ("NotoSansKR.zip", "zip", 52, "NotoSansKR-Bold.otf"),
    ("Montserrat-Bold.ttf", "bin", 55, b"\x00\x01\x00\x00 fake font"),
    ("setup_figma_agent.dmg", "bin", 70, b"fake dmg"),
    ("Blender-4.5-macos.dmg", "bin", 90, b"fake dmg"),
    ("brand_guideline_template.ai", "bin", 27, b"%PDF-1.4 fake ai"),
    ("poster_mockup.psd", "bin", 26, b"8BPS fake psd"),
    ("reference_video.mp4", "bin", 33, b"fake mp4"),
    ("lofi_beats_for_studying.mp3", "bin", 80, b"ID3 fake mp3"),
    ("팀플_회의록_3차.hwp", "bin", 18, b"fake hwp"),
    ("schedule_2026_fall.xlsx", "bin", 38, b"PK fake xlsx"),
    ("untitled.png", "img", 7, (180, 180, 180)),
    ("untitled (2).png", "img", 7, (170, 170, 175)),
    ("통장사본_스캔.jpg", "img", 11, (90, 60, 140)),  # 민감 파일 자동 제외(FS-03) 시연용
]


def pdf_bytes(text: str) -> bytes:
    lines = text.split("\n")
    content = "BT /F1 18 Tf 60 760 Td 24 TL " + " ".join(f"({l}) Tj T*" for l in lines) + " ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def image(path: Path, color, kind: str, i: int) -> None:
    w, h = (1440, 900) if "creenshot" in path.name or "스크린샷" in path.name else (800, 1000) if "포스터" in path.name else (600, 600)
    im = Image.new("RGB", (w // 4, h // 4), color)
    d = ImageDraw.Draw(im)
    d.rectangle([10, 10, w // 4 - 10, h // 4 - 10], outline=(255 - color[0], 255 - color[1], 255 - color[2]), width=3)
    d.text((20, 20), f"sample #{i}", fill=(255 - color[0], 255 - color[1], 255 - color[2]))
    if kind == "gif":
        im.save(path, "GIF")
    elif path.suffix.lower() in (".jpg", ".jpeg"):
        im.save(path, "JPEG", quality=70)
    else:
        im.save(path, "PNG")


def main() -> int:
    OUT.mkdir(exist_ok=True)
    base = datetime(2026, 10, 17, 10, 0)
    dates = {}
    for i, (name, kind, days, data) in enumerate(FILES, 1):
        p = OUT / name
        if kind in ("img", "gif"):
            image(p, data, kind, i)
        elif kind == "pdf":
            p.write_bytes(pdf_bytes(data))
        elif kind == "txt":
            p.write_text(data + "\n", encoding="utf-8")
        elif kind == "zip":
            with zipfile.ZipFile(p, "w") as z:
                z.writestr(data, b"fake font data")
        else:
            p.write_bytes(data)
        dates[name] = (base - timedelta(days=days, hours=i % 9, minutes=i * 7 % 60)).isoformat()
    (OUT / "_dates.json").write_text(json.dumps(dates, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(FILES)}개 파일을 {OUT}에 만들었습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
