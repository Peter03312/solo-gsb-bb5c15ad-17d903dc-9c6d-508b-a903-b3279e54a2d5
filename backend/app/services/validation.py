"""Validation helpers shared by create/update so bad input never half-writes."""
from sqlalchemy.orm import Session

from ..errors import ValidationError
from ..models import Event, Media, Quote
from ..schemas import QuoteIn

# Quotes shorter than this are almost certainly a selection mistake.
MIN_QUOTE_SECONDS = 0.1


def validate_quotes(db: Session, quotes: list[QuoteIn]) -> dict[int, Media]:
    """Validate every quote. Returns media map for reuse by the caller.

    Raises ValidationError listing ALL problems found (index-based) so the
    editor can mark every offending row rather than one at a time.
    """
    problems: list[str] = []
    media_cache: dict[int, Media] = {}

    for i, q in enumerate(quotes):
        prefix = f"第 {i + 1} 条引文："
        if q.end_sec <= q.start_sec:
            problems.append(prefix + "结束秒必须大于开始秒")
        elif q.end_sec - q.start_sec < MIN_QUOTE_SECONDS:
            problems.append(prefix + f"引文时长至少 {MIN_QUOTE_SECONDS} 秒")
        if q.start_sec < 0:
            problems.append(prefix + "开始秒不能为负")

        m = db.get(Media, q.media_id)
        if not m:
            problems.append(prefix + f"引用的音频 #{q.media_id} 不存在或已被删除")
            continue
        media_cache[q.media_id] = m
        if q.end_sec > m.duration_seconds + 0.05:
            problems.append(
                prefix
                + f"结束秒 {_fmt(q.end_sec)} 超出音频时长 {_fmt(m.duration_seconds)}（{m.original_filename}）"
            )
        if q.start_sec >= m.duration_seconds:
            problems.append(
                prefix
                + f"开始秒 {_fmt(q.start_sec)} 已超出音频时长 {_fmt(m.duration_seconds)}"
            )

    if problems:
        raise ValidationError("；".join(problems), problems=problems)
    return media_cache


def replace_quotes(db: Session, event: Event, quotes: list[QuoteIn]) -> None:
    """Delete and re-create the quote set inside the caller's transaction."""
    for old in list(event.quotes):
        db.delete(old)
    db.flush()
    for pos, q in enumerate(quotes):
        m = db.get(Media, q.media_id)
        db.add(
            Quote(
                event_id=event.id,
                media_id=q.media_id,
                speaker=(q.speaker or m.speaker or "").strip() or None,
                start_sec=round(q.start_sec, 3),
                end_sec=round(q.end_sec, 3),
                text=q.text or "",
                position=pos,
            )
        )
    db.flush()


def _fmt(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".") + "s"
