"""Serializers: turn ORM rows into JSON-friendly dicts.

Snapshots are deep copies taken at publish time, so releases never change
when drafts are later edited.
"""
from .models import (
    Event,
    EventSnapshot,
    Media,
    Quote,
    QuoteSnapshot,
    Release,
)


def media_dict(m: Media) -> dict:
    return {
        "id": m.id,
        "original_filename": m.original_filename,
        "speaker": m.speaker,
        "duration_seconds": m.duration_seconds,
        "transcript_kind": m.transcript_kind,
        "created_at": m.created_at.isoformat(),
        "audio_url": f"/api/media/{m.id}/audio",
        "transcript_url": f"/api/media/{m.id}/transcript" if m.transcript_path else None,
    }


def quote_dict(q: Quote) -> dict:
    return {
        "id": q.id,
        "media_id": q.media_id,
        "media_filename": q.media.original_filename if q.media else None,
        "speaker": q.speaker,
        "start_sec": q.start_sec,
        "end_sec": q.end_sec,
        "text": q.text,
        "position": q.position,
        "audio_url": f"/api/media/{q.media_id}/audio",
    }


def quote_snapshot_dict(q: QuoteSnapshot) -> dict:
    return {
        "id": q.id,
        "media_id": q.media_id,
        "media_filename": q.original_filename,
        "speaker": q.speaker,
        "start_sec": q.start_sec,
        "end_sec": q.end_sec,
        "text": q.text,
        "position": q.position,
        "audio_url": f"/api/media/{q.media_id}/audio",
    }


def event_dict(e: Event) -> dict:
    return {
        "id": e.id,
        "title": e.title,
        "event_date": e.event_date,
        "description": e.description,
        "location": e.location,
        "revision": e.revision,
        "updated_at": e.updated_at.isoformat(),
        "quotes": [quote_dict(q) for q in e.quotes],
    }


def event_snapshot_dict(s: EventSnapshot) -> dict:
    return {
        "id": s.id,
        "event_id": s.event_id,
        "title": s.title,
        "event_date": s.event_date,
        "description": s.description,
        "location": s.location,
        "position": s.position,
        "quotes": [quote_snapshot_dict(q) for q in q_sorted(s.quote_snapshots)],
    }


def q_sorted(qs):
    return sorted(qs, key=lambda q: q.position)


def release_dict(r: Release) -> dict:
    return {
        "id": r.id,
        "sequence": r.sequence,
        "label": r.label,
        "note": r.note,
        "published_at": r.published_at.isoformat(),
        "events": [event_snapshot_dict(s) for s in r.event_snapshots],
    }
