import json
import shutil
import struct
import subprocess
import wave
from pathlib import Path

from ..errors import UploadError


def probe_duration(path: Path) -> float:
    """Return audio duration in seconds.

    Prefers ffprobe (installed in the Docker image); falls back to the WAV
    header for uncompressed wav files. Raises UploadError otherwise so a bad
    upload is rejected before any DB row is created.
    """
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            result = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "json",
                    str(path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise UploadError("无法读取音频时长（ffprobe 执行失败）") from exc
        if result.returncode == 0:
            try:
                duration = float(json.loads(result.stdout)["format"]["duration"])
            except (json.JSONDecodeError, KeyError, ValueError):
                raise UploadError("无法解析音频时长，文件可能已损坏")
            if duration <= 0:
                raise UploadError("音频时长必须大于 0")
            return round(duration, 3)

    # Fallback: WAV header parsing (Python stdlib)
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate <= 0:
                    raise UploadError("WAV 采样率无效")
                return round(frames / float(rate), 3)
        except (wave.Error, EOFError, struct.error, OSError) as exc:
            raise UploadError("无法解析 WAV 文件，文件可能已损坏") from exc

    raise UploadError("无法读取音频时长：服务器缺少 ffprobe 且文件不是标准 WAV")
