from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..database import get_db
from ..errors import ConflictError, NotFoundError, ValidationError
from ..models import Event
from ..schemas import EventIn
from ..serializers import event_dict
from ..services.validation import replace_quotes, validate_quotes

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("")
def list_events(db: Session = Depends(get_db)):
    rows = db.scalars(select(Event).order_by(Event.event_date, Event.id)).all()
    return [event_dict(e) for e in rows]


@router.get("/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)):
    e = db.get(Event, event_id)
    if not e:
        raise NotFoundError("事件不存在")
    return event_dict(e)


@router.post("", status_code=201)
def create_event(payload: EventIn, db: Session = Depends(get_db)):
    # Validate all quotes up front: reject the whole request on any bad one.
    validate_quotes(db, payload.quotes)

    event = Event(
        title=payload.title,
        event_date=payload.event_date,
        description=payload.description,
        location=payload.location,
        revision=1,
    )
    db.add(event)
    db.flush()
    replace_quotes(db, event, payload.quotes)
    db.commit()
    db.refresh(event)
    return event_dict(event)


@router.put("/{event_id}")
def update_event(event_id: int, payload: EventIn, db: Session = Depends(get_db)):
    """Optimistic concurrency via revision.

    The row is re-read under a write lock (BEGIN IMMEDIATE) so that two
    concurrent editors cannot both pass the revision check. A mismatch
    returns 409 carrying both sides for the frontend diff dialog.
    """
    if payload.revision is None:
        raise ValidationError("更新事件必须携带 revision")

    validate_quotes(db, payload.quotes)

    db.execute(text("BEGIN IMMEDIATE"))
    event = db.get(Event, event_id)
    if not event:
        db.rollback()
        raise NotFoundError("事件不存在")

    server_revision = event.revision
    if payload.revision != server_revision:
        current = event_dict(event)
        db.rollback()
        raise ConflictError(
            "该事件已被他人修改，请对照后重试",
            server_revision=server_revision,
            client_revision=payload.revision,
            server_event=current,
            submitted={
                "title": payload.title,
                "event_date": payload.event_date,
                "description": payload.description,
                "location": payload.location,
                "quotes": [q.model_dump() for q in payload.quotes],
            },
        )

    event.title = payload.title
    event.event_date = payload.event_date
    event.description = payload.description
    event.location = payload.location
    event.revision = server_revision + 1
    replace_quotes(db, event, payload.quotes)
    db.commit()
    db.refresh(event)
    return event_dict(event)


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    from ..models import EventSnapshot

    referenced = db.scalar(
        select(EventSnapshot.id).where(EventSnapshot.event_id == event_id).limit(1)
    )
    if referenced:
        raise ConflictError("该事件已存在于已发布编年版本中，不能删除（发布版不可变）")
    event = db.get(Event, event_id)
    if not event:
        raise NotFoundError("事件不存在")
    db.delete(event)
    db.commit()
    return None
