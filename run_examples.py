"""Run with .venv/bin/python run_examples.py [auth voice rag]. Ctrl+C stops new servers."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

from dotenv import load_dotenv
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
os.environ.setdefault("FFMPEG_BINARY", imageio_ffmpeg.get_ffmpeg_exe())
SERVICES = {
    "auth": (8080, ROOT / "workplace", ["./gradlew", ":app:run", "--no-configuration-cache"]),
    "voice": (8008, ROOT / "voice-ai_code", [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8008"]),
    "rag": (8001, ROOT / "rag-code-template_ext", [sys.executable, "-m", "uvicorn", "rag_external-web_pdf_closed_llm:app", "--host", "127.0.0.1", "--port", "8001"]),
}

def main():
    names = sys.argv[1:] or list(SERVICES)
    if any(name not in SERVICES for name in names):
        raise SystemExit("Choose: auth voice rag")
    for key in ("JWT_SECRET", "OPENAI_API_KEY"):
        if not os.getenv(key):
            raise SystemExit(f"Set {key} in .env first")
    processes = []
    try:
        for name in names:
            port, cwd, command = SERVICES[name]
            with socket.socket() as sock:
                running = sock.connect_ex(("127.0.0.1", port)) == 0
            if running:
                print(f"{name}: port {port} already running", flush=True)
                continue
            processes.append(subprocess.Popen(command, cwd=cwd))
            print(f"{name}: http://localhost:{port}", flush=True)
        while processes:
            for process in processes:
                if process.poll() is not None:
                    raise SystemExit(f"Server exited with code {process.returncode}")
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()

if __name__ == "__main__":
    main()
