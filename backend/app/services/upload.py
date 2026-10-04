"""Streaming upload to a temp file then atomic commit; supports rollback."""
import os
import tempfile
from pathlib import Path

from fastapi import UploadFile

from .. import config
from ..errors import UploadError

_CHUNK = 1024 * 1024  # 1 MiB


def _safe_suffix(filename: str, allowed: set[str]) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed:
        raise UploadError(f"不支持的文件类型 {suffix or '(无扩展名)'}")
    return suffix


class StagedUpload:
    """A temp file on the same filesystem as the target directory."""

    def __init__(self, suffix: str):
        fd, self.tmp_path = tempfile.mkstemp(suffix=suffix, dir=config.MEDIA_DIR)
        os.close(fd)
        self._path = Path(self.tmp_path)
        self._committed = False

    @property
    def path(self) -> Path:
        return self._path

    async def sink(self, upload: UploadFile, max_bytes: int) -> int:
        written = 0
        try:
            with open(self._path, "wb") as out:
                while True:
                    chunk = await upload.read(_CHUNK)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > max_bytes:
                        raise UploadError(
                            f"上传文件超过大小上限（{config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB）"
                        )
                    out.write(chunk)
        except UploadError:
            self.rollback()
            raise
        except OSError as exc:
            self.rollback()
            raise UploadError(f"文件写入失败：{exc.strerror or exc}") from exc
        return written

    def commit(self, dest: Path) -> None:
        if self._committed:
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.replace(self._path, dest)
        self._committed = True

    def rollback(self) -> None:
        if not self._committed and self._path.exists():
            try:
                self._path.unlink()
            except OSError:
                pass


def audio_suffix(filename: str) -> str:
    return _safe_suffix(filename, config.ALLOWED_AUDIO_EXT)


def transcript_suffix(filename: str) -> str:
    return _safe_suffix(filename, config.ALLOWED_TRANSCRIPT_EXT)
