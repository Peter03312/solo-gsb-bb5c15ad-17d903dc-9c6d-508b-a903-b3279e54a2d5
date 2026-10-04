"""Audio + transcript file serving with HTTP Range support."""
import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..errors import NotFoundError
from ..models import Media

router = APIRouter(prefix="/api/media", tags=["files"])

_AUDIO_MIME = {".mp3": "audio/mpeg", ".wav": "audio/wav"}


def _media_or_404(media_id: int, db: Session) -> Media:
    m = db.get(Media, media_id)
    if not m:
        raise NotFoundError("音频不存在")
    return m


def _ranged_file_response(path: Path, mime: str, request: Request) -> Response:
    if not path.exists():
        raise NotFoundError("音频文件在存储中缺失")

    file_size = path.stat().st_size
    range_header = request.headers.get("range")

    if not range_header or not range_header.startswith("bytes="):
        return FileResponse(path, media_type=mime, status_code=200)

    try:
        spec = range_header.removeprefix("bytes=").split(",")[0].strip()
        start_s, end_s = spec.split("-", 1)
        if start_s == "":  # suffix range: bytes=-N
            length = int(end_s)
            start = max(0, file_size - length)
            end = file_size - 1
        else:
            start = int(start_s)
            end = int(end_s) if end_s else file_size - 1
    except ValueError:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

    end = min(end, file_size - 1)
    if start > end or start >= file_size:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

    chunk_len = end - start + 1
    with open(path, "rb") as f:
        f.seek(start)
        data = f.read(chunk_len)

    return Response(
        content=data,
        status_code=206,
        media_type=mime,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_len),
        },
    )


@router.get("/{media_id}/audio")
def stream_audio(media_id: int, request: Request, db: Session = Depends(get_db)):
    m = _media_or_404(media_id, db)
    mime = _AUDIO_MIME.get(Path(m.stored_audio_path).suffix.lower(), "application/octet-stream")
    return _ranged_file_response(Path(m.stored_audio_path), mime, request)


@router.get("/{media_id}/transcript")
def download_transcript(media_id: int, db: Session = Depends(get_db)):
    m = _media_or_404(media_id, db)
    if not m.transcript_path:
        raise NotFoundError("该音频没有逐字稿")
    path = Path(m.transcript_path)
    if not path.exists():
        raise NotFoundError("逐字稿文件在存储中缺失")
    mime = mimetypes.guess_type(path.name)[0] or "text/plain"
    return FileResponse(path, media_type=mime, filename=path.name)
