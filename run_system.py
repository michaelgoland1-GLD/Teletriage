from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from config.settings import API_PORT, STREAMLIT_PORT

ROOT = Path(__file__).resolve().parent


def main() -> None:
    backend_cmd = [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(API_PORT)]
    frontend_cmd = [sys.executable, "-m", "streamlit", "run", str(ROOT / "frontend" / "app_streamlit.py"), "--server.port", str(STREAMLIT_PORT), "--server.address", "127.0.0.1"]

    backend = subprocess.Popen(backend_cmd, cwd=ROOT)
    try:
        time.sleep(2)
        frontend = subprocess.Popen(frontend_cmd, cwd=ROOT)
        print(f"Backend:  http://127.0.0.1:{API_PORT}")
        print(f"Frontend: http://127.0.0.1:{STREAMLIT_PORT}")
        frontend.wait()
    finally:
        backend.terminate()
        try:
            backend.wait(timeout=5)
        except Exception:
            backend.kill()

if __name__ == "__main__":
    main()
