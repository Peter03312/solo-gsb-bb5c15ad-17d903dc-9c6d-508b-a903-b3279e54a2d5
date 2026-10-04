import os
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "/data")).resolve()
MEDIA_DIR = DATA_DIR / "media"
AUDIO_DIR = MEDIA_DIR / "audio"
TRANSCRIPT_DIR = MEDIA_DIR / "transcripts"
STATIC_DIR = Path(os.getenv("STATIC_DIR", "/app/static")).resolve()
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'museum.db'}")

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "512")) * 1024 * 1024

ALLOWED_AUDIO_EXT = {".mp3", ".wav"}
ALLOWED_TRANSCRIPT_EXT = {".txt", ".srt", ".vtt"}


def ensure_dirs() -> None:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
