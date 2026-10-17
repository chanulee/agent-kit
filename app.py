"""에이전트 키트 켜기:  uv run app.py   (끄기: Ctrl+C)"""
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def load_env():
    """.env 를 읽습니다. 흔한 실수(따옴표, 공백, Windows의 .env.txt)도 받아 줍니다."""
    for name in (".env", ".env.txt", "prototype/tests/.env"):
        p = ROOT / name
        if p.exists():
            for line in p.read_text(encoding="utf-8-sig").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    v = v.strip().strip('"').strip("'").strip()
                    if v:
                        os.environ.setdefault(k.strip(), v)


def _free(port: int) -> bool:
    """포트가 비었는지. 연결해 보기(connect)는 Windows에서 몇 초씩 걸려서 직접 잡아 봅니다(bind)."""
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def main():
    load_env()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import uvicorn
    from engine.server import create_app
    port = next((p for p in range(8765, 8785) if _free(p)), 8765)
    url = f"http://127.0.0.1:{port}"
    print(f"\n  에이전트 대시보드 → {url}\n  끄려면 Ctrl+C\n")
    if "--no-browser" not in sys.argv:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
