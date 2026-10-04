from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..errors import ConflictError, NotFoundError, ValidationError
from ..models import (
    Event,
    EventSnapshot,
    QuoteSnapshot,
    Release,
)
from ..schemas import PublishIn
from ..serializers import release_dict

router = APIRouter(prefix="/api/releases", tags=["releases"])


@router.get("")
def list_releases(db: Session = Depends(get_db)):
    rows = db.scalars(select(Release).order_by(Release.sequence.desc())).all()
    return [
        {
            "id": r.id,
            "sequence": r.sequence,
            "label": r.label,
            "note": r.note,
            "published_at": r.published_at.isoformat(),
            "event_count": len(r.event_snapshots),
        }
        for r in rows
    ]


@router.get("/latest")
def get_latest_release(db: Session = Depends(get_db)):
    r = db.scalars(select(Release).order_by(Release.sequence.desc()).limit(1)).first()
    if not r:
        raise NotFoundError("尚未发布任何编年版本")
    return release_dict(r)


@router.get("/{release_id}")
def get_release(release_id: int, db: Session = Depends(get_db)):
    r = db.get(Release, release_id)
    if not r:
        raise NotFoundError("编年版本不存在")
    return release_dict(r)


@router.post("", status_code=201)
def publish_release(payload: PublishIn, db: Session = Depends(get_db)):
    """Create an immutable snapshot of ALL current drafts ordered by date.

    BEGIN IMMEDIATE serializes two publishers; the unique sequence constraint
    is the final guard. Nothing in a release is ever updated afterwards, and
    the snapshot stores its own copies of every field and quote.
    """
    events = list(db.scalars(select(Event).order_by(Event.event_date, Event.id)).all())
    if not events:
        raise ValidationError("当前没有任何事件草稿，无法发布")

    db.execute(text("BEGIN IMMEDIATE"))

    max_seq = db.scalar(select(func.coalesce(func.max(Release.sequence), 0)))
    release = Release(sequence=max_seq + 1, label=payload.label, note=payload.note)
    db.add(release)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("另一个发布操作正在进行，请刷新后重试") from exc

    for pos, event in enumerate(events):
        snap = EventSnapshot(
            release_id=release.id,
            event_id=event.id,
            title=event.title,
            event_date=event.event_date,
            description=event.description,
            location=event.location,
            position=pos,
        )
        db.add(snap)
        db.flush()
        for qpos, q in enumerate(event.quotes):
            db.add(
                QuoteSnapshot(
                    event_snapshot_id=snap.id,
                    media_id=q.media_id,
                    original_filename=q.media.original_filename if q.media else "(已删除)",
                    speaker=q.speaker,
                    start_sec=q.start_sec,
                    end_sec=q.end_sec,
                    text=q.text,
                    position=qpos,
                )
            )

    db.commit()
    db.refresh(release)
    return release_dict(release)
