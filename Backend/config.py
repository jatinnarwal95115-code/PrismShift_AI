"""Central settings. Values can be overridden in Backend/.env or the environment."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_env_file() -> None:
    env_path = BASE_DIR / ".env"

    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:latest")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

# Local models can be slow on the first request while the model loads.
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "300"))

SESSION_DAYS = int(os.getenv("SESSION_DAYS", "30"))

# Any localhost / 127.0.0.1 origin (Live Server, Vite, FastAPI itself ...).
CORS_ORIGIN_REGEX = os.getenv(
    "CORS_ORIGIN_REGEX",
    r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
)
