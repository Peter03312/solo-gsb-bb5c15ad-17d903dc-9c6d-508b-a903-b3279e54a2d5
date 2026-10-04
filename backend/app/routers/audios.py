"""音频与逐字稿 API：原子上传、列表/详情、删除保护、支持 Range 的流式播放。"""
import os
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from .. import config
from ..database import get_conn

router = APIRouter(prefix="/api/audios", tags=["audios"])

_CHUNK = 1024 * 1024


def _audio_duration(path: Path) -> float | None:
    try:
        from mutagen import File as MutagenFile

        media = MutagenFile(path)
        if media is not None and media.info is not None:
            return float(media.info.length)
    except Exception:
        return None
    return None


def _serialize_audio(row, *, with_transcript: bool = False) -> dict:
    data = {
        "id": row["id"],
        "original_name": row["original_name"],
        "content_type": row["content_type"],
        "size_bytes": row["size_bytes"],
        "duration": row["duration"],
        "created_at": row["created_at"],
    }
    if with_transcript:
        data["transcript_text"] = row["transcript_text"]
    return data


@router.get("")
def list_audios(conn=Depends(get_conn)):
    rows = conn.execute("SELECT * FROM audios ORDER BY created_at DESC, id DESC").fetchall()
    return [_serialize_audio(r) for r in rows]


@router.get("/{audio_id}")
def get_audio(audio_id: int, conn=Depends(get_conn)):
    row = conn.execute("SELECT * FROM audios WHERE id = ?", (audio_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="音频不存在")
    return _serialize_audio(row, with_transcript=True)


@router.post("", status_code=201)
async def upload_audio(
    file: UploadFile = File(...),
    transcript_text: str | None = Form(None),
    transcript_file: UploadFile | None = File(None),
    conn=Depends(get_conn),
):
    """原子上传：先校验并写临时文件、解析时长，全部成功后才写库并重命名落位。

    任一步失败都清理临时文件，数据库不产生记录，绝无半成品。
    """
    original_name = file.filename or ""
    ext = Path(original_name).suffix.lower()
    if ext not in config.AUDIO_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 MP3 / WAV 音频文件")
    content_type = config.AUDIO_TYPES[ext]

    # 逐字稿：文件与内联文本二选一
    transcript_body = transcript_text
    transcript_format = "inline" if transcript_text is not None else None
    if transcript_file is not None:
        if transcript_body:
            raise HTTPException(status_code=400, detail="逐字稿文件与文本只能提供一种")
        raw = await transcript_file.read(config.MAX_TRANSCRIPT_BYTES + 1)
        if len(raw) > config.MAX_TRANSCRIPT_BYTES:
            raise HTTPException(status_code=400, detail="逐字稿超过 5MB 上限")
        try:
            transcript_body = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="逐字稿必须为 UTF-8 文本")
        transcript_format = "file"

    stored_name = f"{uuid.uuid4().hex}{ext}"
    final_path = config.AUDIO_DIR / stored_name
    tmp_path = config.AUDIO_DIR / f"{stored_name}.part"

    size = 0
    try:
        with open(tmp_path, "wb") as out:
            while True:
                chunk = await file.read(_CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > config.MAX_AUDIO_BYTES:
                    raise HTTPException(status_code=400, detail="音频超过 200MB 上限")
                out.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="音频文件为空")

        duration = _audio_duration(tmp_path)
        if duration is None:
            raise HTTPException(status_code=400, detail="无法解析音频，文件可能已损坏")

        cur = conn.execute(
            """INSERT INTO audios
                   (original_name, stored_name, content_type, size_bytes, duration,
                    transcript_text, transcript_format)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (original_name, stored_name, content_type, size, duration,
             transcript_body, transcript_format),
        )
        audio_id = cur.lastrowid
        conn.commit()
    except HTTPException:
        conn.rollback()
        tmp_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        conn.rollback()
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"上传失败：{exc}")

    # 数据库落定后原子重命名为正式文件
    try:
        os.replace(tmp_path, final_path)
    except OSError:
        # 极端情况：回滚数据库并清理
        conn.execute("DELETE FROM audios WHERE id = ?", (audio_id,))
        conn.commit()
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="音频落盘失败，请重试")

    row = conn.execute("SELECT * FROM audios WHERE id = ?", (audio_id,)).fetchone()
    return _serialize_audio(row, with_transcript=True)


@router.delete("/{audio_id}", status_code=204)
def delete_audio(audio_id: int, conn=Depends(get_conn)):
    row = conn.execute("SELECT id, stored_name, original_name FROM audios WHERE id = ?",
                       (audio_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="音频不存在")

    # 已被发布版引用的音频不可删除；草稿引用同样拦截并给出明确提示
    pub = conn.execute(
        """SELECT p.id AS pid, p.version, pe.event_title
             FROM publication_entry_quotes q
             JOIN publication_entries pe ON pe.id = q.entry_id
             JOIN publications p ON p.id = pe.publication_id
            WHERE q.audio_id = ? LIMIT 1""",
        (audio_id,),
    ).fetchone()
    if pub is not None:
        raise HTTPException(
            status_code=409,
            detail=f"音频已被发布版 v{pub['version']} 引用（事件：{pub['event_title']}），不可删除",
        )
    draft = conn.execute(
        """SELECT e.id, e.title FROM event_quotes q
             JOIN events e ON e.id = q.event_id
            WHERE q.audio_id = ? LIMIT 1""",
        (audio_id,),
    ).fetchone()
    if draft is not None:
        raise HTTPException(
            status_code=409,
            detail=f"音频正被草稿事件「{draft['title']}」引用，请先移除相关引文",
        )

    conn.execute("DELETE FROM audios WHERE id = ?", (audio_id,))
    conn.commit()
    (config.AUDIO_DIR / row["stored_name"]).unlink(missing_ok=True)


@router.get("/{audio_id}/stream")
def stream_audio(audio_id: int, request: Request, conn=Depends(get_conn)):
    """音频流：支持 Range 请求，前端播放器可从引文起止秒跳转。"""
    row = conn.execute("SELECT * FROM audios WHERE id = ?", (audio_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="音频不存在")

    path = config.AUDIO_DIR / row["stored_name"]
    if not path.exists():
        # 数据库有记录但文件缺失属于存储故障，明确报错而非静默
        raise HTTPException(status_code=500, detail="音频文件缺失，请联系管理员")

    file_size = path.stat().st_size
    range_header = request.headers.get("range")
    start, end = 0, file_size - 1
    status = 200
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Content-Type": row["content_type"],
    }

    if range_header:
        m = re.match(r"bytes=(\d*)-(\d*)$", range_header.strip())
        if not m:
            raise HTTPException(status_code=416, detail="Range 格式无效")
        g1, g2 = m.group(1), m.group(2)
        if g1 == "" and g2:
            # bytes=-N：最后 N 字节
            suffix = int(g2)
            start = max(0, file_size - suffix)
        else:
            start = int(g1 or 0)
            if g2:
                end = int(g2)
        if start >= file_size or end >= file_size or start > end:
            raise HTTPException(status_code=416, detail="请求范围超出文件大小")
        status = 206
        headers["Content-Length"] = str(end - start + 1)
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

    def iterfile():
        with open(path, "rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                data = f.read(min(_CHUNK, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    return StreamingResponse(iterfile(), status_code=status, headers=headers)
