from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Media(Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_audio_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    transcript_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    transcript_kind: Mapped[str | None] = mapped_column(String(8), nullable=True)  # txt|srt|vtt
    speaker: Mapped[str | None] = mapped_column(String(256), nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    event_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY or YYYY-MM-DD
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    location: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    quotes: Mapped[list["Quote"]] = relationship(
        back_populates="event", cascade="all, delete-orphan", order_by="Quote.position"
    )


class Quote(Base):
    __tablename__ = "quotes"
    __table_args__ = (Index("ix_quotes_media_id", "media_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    media_id: Mapped[int] = mapped_column(ForeignKey("media.id"), nullable=False)
    speaker: Mapped[str | None] = mapped_column(String(256), nullable=True)
    start_sec: Mapped[float] = mapped_column(Float, nullable=False)
    end_sec: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    event: Mapped[Event] = relationship(back_populates="quotes")
    media: Mapped[Media] = relationship()


class Release(Base):
    __tablename__ = "releases"
    __table_args__ = (UniqueConstraint("sequence", name="uq_releases_sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    event_snapshots: Mapped[list["EventSnapshot"]] = relationship(
        back_populates="release", cascade="all, delete-orphan", order_by="EventSnapshot.position"
    )


class EventSnapshot(Base):
    __tablename__ = "event_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    release_id: Mapped[int] = mapped_column(
        ForeignKey("releases.id", ondelete="CASCADE"), nullable=False
    )
    event_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    event_date: Mapped[str] = mapped_column(String(10), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    location: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    release: Mapped[Release] = relationship(back_populates="event_snapshots")
    quote_snapshots: Mapped[list["QuoteSnapshot"]] = relationship(
        back_populates="event_snapshot",
        cascade="all, delete-orphan",
        order_by="QuoteSnapshot.position",
    )


class QuoteSnapshot(Base):
    __tablename__ = "quote_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("event_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    media_id: Mapped[int] = mapped_column(Integer, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    speaker: Mapped[str | None] = mapped_column(String(256), nullable=True)
    start_sec: Mapped[float] = mapped_column(Float, nullable=False)
    end_sec: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    event_snapshot: Mapped[EventSnapshot] = relationship(back_populates="quote_snapshots")
