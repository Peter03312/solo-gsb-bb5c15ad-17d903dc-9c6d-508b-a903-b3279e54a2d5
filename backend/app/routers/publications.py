"""编年发布 API：生成不可变快照版本，后续改稿不影响历史版本。"""
from fastapi import APIRouter, Depends, HTTPException

from ..database import get_conn
from ..schemas import PublishIn

router = APIRouter(prefix="/api/publications", tags=["publications"])


def _quote_rows(conn, entry_id: int) -> list[dict]:
    rows = conn.execute(
        """SELECT audio_id, speaker, start_sec, end_sec, quote_text, position
             FROM publication_entry_quotes WHERE entry_id = ?
            ORDER BY position, id""",
        (entry_id,),
    ).fetchall()
    result = []
    for r in rows:
        audio = conn.execute(
            "SELECT original_name, content_type FROM audios WHERE id = ?",
            (r["audio_id"],),
        ).fetchone()
        result.append({
            "audio_id": r["audio_id"],
            "audio_name": audio["original_name"] if audio else "(音频已移除)",
            "speaker": r["speaker"],
            "start_sec": r["start_sec"],
            "end_sec": r["end_sec"],
            "quote_text": r["quote_text"],
        })
    return result


def _serialize_publication(conn, row) -> dict:
    entries = conn.execute(
        """SELECT * FROM publication_entries
            WHERE publication_id = ? ORDER BY position, id""",
        (row["id"],),
    ).fetchall()
    data = []
    for e in entries:
        data.append({
            "event_id": e["event_id"],
            "event_title": e["event_title"],
            "event_date": e["event_date"],
            "event_description": e["event_description"],
            "event_revision": e["event_revision"],
            "entry_type": e["entry_type"],
            "quotes": _quote_rows(conn, e["id"]),
        })
    return {
        "id": row["id"],
        "version": row["version"],
        "note": row["note"],
        "created_at": row["created_at"],
        "entries": data,
    }


@router.get("")
def list_publications(conn=Depends(get_conn)):
    rows = conn.execute(
        "SELECT * FROM publications ORDER BY version DESC"
    ).fetchall()
    return [
        {
            "id": r["id"],
            "version": r["version"],
            "note": r["note"],
            "created_at": r["created_at"],
            "entry_count": conn.execute(
                "SELECT COUNT(*) FROM publication_entries WHERE publication_id = ?",
                (r["id"],),
            ).fetchone()[0],
        }
        for r in rows
    ]


@router.get("/{publication_id}")
def get_publication(publication_id: int, conn=Depends(get_conn)):
    row = conn.execute(
        "SELECT * FROM publications WHERE id = ?", (publication_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="发布版本不存在")
    return _serialize_publication(conn, row)


@router.post("", status_code=201)
def publish(payload: PublishIn, conn=Depends(get_conn)):
    """把当前全部草稿事件及其引文整体快照为一个新版本。

    发布期间加写锁串行化，保证版本号连续、快照与当前数据一致。
    """
    try:
        conn.execute("BEGIN IMMEDIATE")
        events = conn.execute(
            "SELECT * FROM events ORDER BY event_date, id"
        ).fetchall()
        if not events:
            raise HTTPException(status_code=400, detail="暂无可发布的事件草稿")

        last = conn.execute("SELECT MAX(version) FROM publications").fetchone()[0]
        version = (last or 0) + 1

        cur = conn.execute(
            "INSERT INTO publications (version, note) VALUES (?, ?)",
            (version, payload.note.strip()),
        )
        pub_id = cur.lastrowid

        for position, ev in enumerate(events):
            quotes = conn.execute(
                "SELECT * FROM event_quotes WHERE event_id = ? ORDER BY position, id",
                (ev["id"],),
            ).fetchall()
            entry_type = "multiple" if len(quotes) > 1 else "single"
            ecur = conn.execute(
                """INSERT INTO publication_entries
                       (publication_id, event_id, event_title, event_date,
                        event_description, event_revision, entry_type, position)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (pub_id, ev["id"], ev["title"], ev["event_date"],
                 ev["description"], ev["revision"], entry_type, position),
            )
            entry_id = ecur.lastrowid
            for qpos, q in enumerate(quotes):
                conn.execute(
                    """INSERT INTO publication_entry_quotes
                           (entry_id, audio_id, speaker, start_sec, end_sec,
                            quote_text, position)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (entry_id, q["audio_id"], q["speaker"], q["start_sec"],
                     q["end_sec"], q["quote_text"], qpos),
                )
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"发布失败：{exc}")

    row = conn.execute("SELECT * FROM publications WHERE id = ?", (pub_id,)).fetchone()
    return _serialize_publication(conn, row)
