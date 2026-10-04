"""事件草稿与引文 API。"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlite3 import IntegrityError

from ..database import get_conn
from ..schemas import EventIn, QuoteIn

router = APIRouter(prefix="/api/events", tags=["events"])

# 时长校验容差：MP3 时长由编码器估算，允许轻微越界
DURATION_EPS = 0.1


def _serialize_event(conn, event_row) -> dict:
    quotes = conn.execute(
        """SELECT q.id, q.audio_id, q.speaker, q.start_sec, q.end_sec,
                  q.quote_text, q.position,
                  a.original_name AS audio_name, a.duration AS audio_duration,
                  a.content_type
             FROM event_quotes q JOIN audios a ON a.id = q.audio_id
            WHERE q.event_id = ? ORDER BY q.position, q.id""",
        (event_row["id"],),
    ).fetchall()
    return {
        "id": event_row["id"],
        "title": event_row["title"],
        "event_date": event_row["event_date"],
        "description": event_row["description"],
        "revision": event_row["revision"],
        "created_at": event_row["created_at"],
        "updated_at": event_row["updated_at"],
        "quotes": [dict(q) for q in quotes],
    }


def _validate_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise HTTPException(status_code=400, detail="事件日期格式无效，应为 YYYY-MM-DD")


def _validate_quotes(conn, quotes: list[QuoteIn]) -> None:
    if not quotes:
        raise HTTPException(status_code=400, detail="至少需要一条引文")
    for idx, q in enumerate(quotes):
        if q.start_sec >= q.end_sec:
            raise HTTPException(status_code=400, detail=f"第 {idx + 1} 条引文：起始秒须小于结束秒")
        audio = conn.execute(
            "SELECT id, duration FROM audios WHERE id = ?", (q.audio_id,)
        ).fetchone()
        if audio is None:
            raise HTTPException(status_code=400, detail=f"第 {idx + 1} 条引文：所选音频不存在")
        if audio["duration"] is not None:
            if q.start_sec < 0 or q.end_sec > audio["duration"] + DURATION_EPS:
                raise HTTPException(
                    status_code=400,
                    detail=f"第 {idx + 1} 条引文：起止秒超出音频时长 "
                           f"({audio['duration']:.1f} 秒)",
                )


def _save_quote_rows(conn, event_id: int, quotes: list[QuoteIn]) -> None:
    conn.execute("DELETE FROM event_quotes WHERE event_id = ?", (event_id,))
    for position, q in enumerate(quotes):
        conn.execute(
            """INSERT INTO event_quotes
                   (event_id, audio_id, speaker, start_sec, end_sec, quote_text, position)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (event_id, q.audio_id, q.speaker.strip(), q.start_sec, q.end_sec,
             q.quote_text.strip(), position),
        )


@router.get("")
def list_events(conn=Depends(get_conn)):
    rows = conn.execute("SELECT * FROM events ORDER BY event_date, id").fetchall()
    return [_serialize_event(conn, r) for r in rows]


@router.get("/{event_id}")
def get_event(event_id: int, conn=Depends(get_conn)):
    row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="事件不存在")
    return _serialize_event(conn, row)


@router.post("", status_code=201)
def create_event(payload: EventIn, conn=Depends(get_conn)):
    event_date = _validate_date(payload.event_date)
    try:
        _validate_quotes(conn, payload.quotes)
        cur = conn.execute(
            "INSERT INTO events (title, event_date, description) VALUES (?, ?, ?)",
            (payload.title.strip(), event_date, payload.description.strip()),
        )
        event_id = cur.lastrowid
        _save_quote_rows(conn, event_id, payload.quotes)
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except (IntegrityError, ValidationError, Exception) as exc:
        # 任何失败均回滚，绝不留下无引文的半成品事件
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"保存失败：{exc}")
    row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    return _serialize_event(conn, row)


@router.put("/{event_id}")
def update_event(event_id: int, payload: EventIn, conn=Depends(get_conn)):
    row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="事件不存在或已被删除")

    # 乐观并发控制：revision 不匹配说明他人已先保存
    if payload.base_revision is not None and payload.base_revision != row["revision"]:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "该事件已被他人修订，请对照最新版本后重试",
                "server_event": _serialize_event(conn, row),
                "submitted": payload.model_dump(),
            },
        )

    event_date = _validate_date(payload.event_date)
    try:
        _validate_quotes(conn, payload.quotes)
        conn.execute(
            """UPDATE events
                  SET title = ?, event_date = ?, description = ?,
                      revision = revision + 1,
                      updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
                WHERE id = ?""",
            (payload.title.strip(), event_date, payload.description.strip(), event_id),
        )
        _save_quote_rows(conn, event_id, payload.quotes)
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"保存失败：{exc}")
    row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    return _serialize_event(conn, row)


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: int, conn=Depends(get_conn)):
    row = conn.execute("SELECT id FROM events WHERE id = ?", (event_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="事件不存在")
    conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
