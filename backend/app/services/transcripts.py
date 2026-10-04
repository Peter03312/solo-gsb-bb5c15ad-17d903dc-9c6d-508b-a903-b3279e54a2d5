"""SRT / WebVTT transcript parsing."""
import re
from dataclasses import dataclass
from pathlib import Path

from ..errors import UploadError

_TS = r"(\d{1,2}):(\d{2}):(\d{2})[.,](\d{1,3})"
_TIME_LINE = re.compile(rf"^{_TS}\s*-->\s*{_TS}")
_VTT_TS_SHORT = re.compile(r"^(\d{1,2}):(\d{2})[.,](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2})[.,](\d{1,3})")


@dataclass
class Cue:
    start: float
    end: float
    text: str


def _to_seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000.0


def parse_transcript(path: Path, kind: str) -> list[Cue]:
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UploadError("逐字稿必须是 UTF-8 编码") from exc

    if kind == "vtt":
        return _parse_vtt(raw)
    return _parse_srt(raw)


def _parse_srt(raw: str) -> list[Cue]:
    cues: list[Cue] = []
    blocks = re.split(r"\n\s*\n", raw.replace("\r\n", "\n").replace("\r", "\n"))
    for block in blocks:
        lines = [ln for ln in block.split("\n") if ln.strip() != ""]
        idx = 0
        if lines and lines[0].strip().isdigit():
            idx = 1
        if idx >= len(lines):
            continue
        m = _TIME_LINE.match(lines[idx].strip())
        if not m:
            continue
        g = m.groups()
        start = _to_seconds(*g[0:4])
        end = _to_seconds(*g[4:8])
        text = "\n".join(lines[idx + 1 :]).strip()
        text = _strip_tags(text)
        if text and end > start:
            cues.append(Cue(round(start, 3), round(end, 3), text))
    if not cues:
        raise UploadError("SRT 逐字稿中未找到任何有效字幕条目")
    return cues


def _parse_vtt(raw: str) -> list[Cue]:
    cues: list[Cue] = []
    blocks = re.split(r"\n\s*\n", raw.replace("\r\n", "\n").replace("\r", "\n"))
    for block in blocks:
        lines = [ln for ln in block.split("\n") if ln.strip() != ""]
        if not lines:
            continue
        time_idx = -1
        start = end = None
        for i, ln in enumerate(lines):
            stripped = ln.strip()
            m = _TIME_LINE.match(stripped)
            if m:
                g = m.groups()
                start = _to_seconds(*g[0:4])
                end = _to_seconds(*g[4:8])
                time_idx = i
                break
            m2 = _VTT_TS_SHORT.match(stripped)
            if m2:
                g = m2.groups()
                start = int(g[0]) * 60 + int(g[1]) + int(g[2].ljust(3, "0")) / 1000.0
                end = int(g[3]) * 60 + int(g[4]) + int(g[5].ljust(3, "0")) / 1000.0
                time_idx = i
                break
        if time_idx < 0:
            continue
        text = _strip_tags("\n".join(lines[time_idx + 1 :]).strip())
        if text and end > start:
            cues.append(Cue(round(start, 3), round(end, 3), text))
    if not cues:
        raise UploadError("WebVTT 逐字稿中未找到任何有效字幕条目")
    return cues


def _strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\{\\[^}]+\}", "", text)
    return text.strip()


def cues_between(cues: list[Cue], start: float, end: float) -> list[Cue]:
    """Cues whose interval overlaps [start, end] (any overlap counts)."""
    return [c for c in cues if c.end > start and c.start < end]
