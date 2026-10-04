"""SQLite 连接管理与建表初始化。

- 使用 WAL 提升读写并发；
- 每个连接开启外键约束；
- 应用启动时自动建表，已存在则不改动（幂等）。
"""
import sqlite3
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS audios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_name TEXT NOT NULL,
    stored_name TEXT NOT NULL UNIQUE,
    content_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    duration REAL,
    transcript_text TEXT,
    transcript_format TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    event_date TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS event_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    audio_id INTEGER NOT NULL REFERENCES audios(id) ON DELETE RESTRICT,
    speaker TEXT NOT NULL DEFAULT '',
    start_sec REAL NOT NULL,
    end_sec REAL NOT NULL,
    quote_text TEXT NOT NULL DEFAULT '',
    position INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- 发布动作产生不可变编年版本
CREATE TABLE IF NOT EXISTS publications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version INTEGER NOT NULL UNIQUE,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- 发布快照：事件与引文在发布瞬间的完整内容拷贝
CREATE TABLE IF NOT EXISTS publication_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    publication_id INTEGER NOT NULL REFERENCES publications(id) ON DELETE CASCADE,
    -- 事件被删除时仅断开溯源链接，快照内容本身不受影响
    event_id INTEGER REFERENCES events(id) ON DELETE SET NULL,
    event_title TEXT NOT NULL,
    event_date TEXT NOT NULL,
    event_description TEXT NOT NULL DEFAULT '',
    event_revision INTEGER NOT NULL,
    entry_type TEXT NOT NULL,           -- single | multiple
    position INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS publication_entry_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES publication_entries(id) ON DELETE CASCADE,
    audio_id INTEGER NOT NULL REFERENCES audios(id) ON DELETE RESTRICT,
    speaker TEXT NOT NULL DEFAULT '',
    start_sec REAL NOT NULL,
    end_sec REAL NOT NULL,
    quote_text TEXT NOT NULL DEFAULT '',
    position INTEGER NOT NULL DEFAULT 0
);
"""


def init_db() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    config.TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def get_conn():
    """FastAPI 请求依赖：yield 一个行工厂连接，请求结束自动关闭。"""
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()
