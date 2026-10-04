import os
from pathlib import Path

# 数据根目录：音频、逐字稿与 SQLite 数据库均存放于此，便于挂载持久化卷
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data")).resolve()
AUDIO_DIR = DATA_DIR / "audio"
TRANSCRIPT_DIR = DATA_DIR / "transcripts"
DB_PATH = DATA_DIR / "workbench.db"

# 单文件大小上限（字节）
MAX_AUDIO_BYTES = int(os.environ.get("MAX_AUDIO_BYTES", 200 * 1024 * 1024))
MAX_TRANSCRIPT_BYTES = int(os.environ.get("MAX_TRANSCRIPT_BYTES", 5 * 1024 * 1024))

# 允许的音频扩展名 -> MIME
AUDIO_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
}

# 静态前端构建产物目录（Docker 中由构建阶段拷入）
STATIC_DIR = Path(os.environ.get("STATIC_DIR", os.path.join(os.path.dirname(__file__), "..", "static")))
