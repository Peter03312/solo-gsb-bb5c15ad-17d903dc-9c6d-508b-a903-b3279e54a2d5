import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import config
from ..database import get_db
from ..errors import ConflictError, NotFoundError, UploadError, ValidationError
from ..models import Media, Quote, QuoteSnapshot
from ..serializers import media_dict
from ..services.audio import probe_duration
from ..services.transcripts import cues_between, parse_transcript
from ..services.upload import (
    StagedUpload,
    audio_suffix,
    transcript_suffix,
)

router = APIRouter(prefix="/api/media", tags=["media"])


@router.get("")
def list_media(db: Session = Depends(get_db)):
    rows = db.scalars(select(Media).order_by(Media.created_at.desc(), Media.id.desc())).all()
    return [media_dict(m) for m in rows]


@router.get("/{media_id}")
def get_media(media_id: int, db: Session = Depends(get_db)):
    m = db.get(Media, media_id)
    if not m:
        raise NotFoundError("音频不存在")
    return media_dict(m)


@router.post("", status_code=201)
async def upload_media(
    audio: UploadFile = File(...),
    transcript: UploadFile | None = File(default=None),
    speaker: str = Form(default=""),
    db: Session = Depends(get_db),
):
    """Atomically ingest an audio file (+ optional transcript).

    Both files are fully staged on disk and the audio is probed BEFORE any DB
    row is written. Any failure rolls the staged files back, so a failed
    upload never leaves a half-created record or orphaned file.
    """
    if not audio.filename:
        raise ValidationError("缺少音频文件名")
    try:
        a_suffix = audio_suffix(audio.filename)
    except UploadError:
        raise

    audio_stage = StagedUpload(a_suffix)
    transcript_stage: StagedUpload | None = None
    transcript_kind: str | None = None
    committed_paths: list[Path] = []
    try:
        await audio_stage.sink(audio, config.MAX_UPLOAD_BYTES)
        duration = probe_duration(audio_stage.path)

        if transcript is not None and transcript.filename:
            t_suffix = transcript_suffix(transcript.filename)
            transcript_kind = t_suffix.lstrip(".")
            transcript_stage = StagedUpload(t_suffix)
            await transcript_stage.sink(transcript, config.MAX_UPLOAD_BYTES)
            if transcript_kind in {"srt", "vtt"}:
                parse_transcript(transcript_stage.path, transcript_kind)  # raises if malformed
            else:
                transcript_stage.path.read_text(encoding="utf-8", errors="strict")

        token = uuid.uuid4().hex
        audio_dest = config.AUDIO_DIR / f"{token}{a_suffix}"
        t_dest = (
            config.TRANSCRIPT_DIR / f"{token}{transcript_stage.path.suffix}"
            if transcript_stage is not None
            else None
        )

        # First make the DB row survive inside the transaction; only then move
        # the staged files into their final place and commit. Any failure in
        # between rolls the DB back and removes any already-finalized files,
        # so a failed upload can never leave a half-created record.
        media = Media(
            original_filename=audio.filename,
            stored_audio_path=str(audio_dest),
            transcript_path=str(t_dest) if t_dest else None,
            transcript_kind=transcript_kind,
            speaker=speaker.strip() or None,
            duration_seconds=duration,
        )
        db.add(media)
        db.flush()

        audio_stage.commit(audio_dest)
        committed_paths.append(audio_dest)
        if transcript_stage is not None and t_dest is not None:
            transcript_stage.commit(t_dest)
            committed_paths.append(t_dest)

        db.commit()
        db.refresh(media)
        return media_dict(media)
    except UnicodeDecodeError as exc:
        db.rollback()
        for p in committed_paths:
            p.unlink(missing_ok=True)
        raise UploadError("逐字稿必须是 UTF-8 编码的文本文件") from exc
    except Exception:
        db.rollback()
        for p in committed_paths:
            p.unlink(missing_ok=True)
        raise
    finally:
        audio_stage.rollback()  # no-op once committed
        if transcript_stage is not None:
            transcript_stage.rollback()


@router.delete("/{media_id}", status_code=204)
def delete_media(media_id: int, db: Session = Depends(get_db)):
    m = db.get(Media, media_id)
    if not m:
        raise NotFoundError("音频不存在")

    draft_count = db.scalar(select(func.count()).select_from(Quote).where(Quote.media_id == media_id))
    released_count = db.scalar(
        select(func.count()).select_from(QuoteSnapshot).where(QuoteSnapshot.media_id == media_id)
    )
    if draft_count or released_count:
        parts = []
        if draft_count:
            parts.append(f"{draft_count} 条草稿引文")
        if released_count:
            parts.append(f"{released_count} 条已发布引文")
        raise ConflictError(f"该音频被 {'、'.join(parts)} 引用，不可删除")

    audio_path = m.stored_audio_path
    transcript_path = m.transcript_path
    db.delete(m)
    db.commit()
    # Files are removed only after the DB commit succeeds.
    for p in (audio_path, transcript_path):
        if p:
            try:
                Path(p).unlink(missing_ok=True)
            except OSError:
                pass
    return None


@router.get("/{media_id}/cues")
def get_cues(media_id: int, db: Session = Depends(get_db)):
    m = db.get(Media, media_id)
    if not m:
        raise NotFoundError("音频不存在")
    if not m.transcript_path or m.transcript_kind not in {"srt", "vtt"}:
        return {"cues": []}
    cues = parse_transcript(Path(m.transcript_path), m.transcript_kind)
    return {"cues": [c.__dict__ for c in cues]}


@router.get("/{media_id}/quote-text")
def get_quote_text(
    media_id: int,
    start: float,
    end: float,
    db: Session = Depends(get_db),
):
    """Best-effort: extract transcript text overlapping [start, end]."""
    from ..services.transcripts import cues_between

    m = db.get(Media, media_id)
    if not m:
        raise NotFoundError("音频不存在")
    if start < 0 or end <= start:
        raise ValidationError("无效的起止秒")
    if not m.transcript_path:
        return {"text": ""}

    path = Path(m.transcript_path)
    if m.transcript_kind in {"srt", "vtt"}:
        cues = parse_transcript(path, m.transcript_kind)
        picked = cues_between(cues, start, end)
        return {"text": "\n".join(c.text for c in picked)}
    return {"text": ""}
