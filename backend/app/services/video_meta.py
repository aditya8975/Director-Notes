"""
Video metadata + thumbnail extraction using ffmpeg/ffprobe.

Requires ffmpeg to be installed on the system and available on PATH.
On macOS: brew install ffmpeg
On Windows: download from ffmpeg.org and add to PATH
On Linux: apt install ffmpeg
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mxf"}


class FFmpegNotFoundError(RuntimeError):
    pass


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError as e:
        raise FFmpegNotFoundError(
            "ffmpeg/ffprobe not found on PATH. Install ffmpeg and restart the server."
        ) from e


def probe_video(filepath: str) -> dict:
    """Returns duration, width, height, fps, codec for a video file using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", filepath,
    ]
    result = _run(cmd)
    data = json.loads(result.stdout)

    video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    fmt = data.get("format", {})

    duration = float(fmt.get("duration", 0)) if fmt.get("duration") else None
    width = height = None
    fps = None
    codec = None

    if video_stream:
        width = video_stream.get("width")
        height = video_stream.get("height")
        codec = video_stream.get("codec_name")
        rate = video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")
        if rate and rate != "0/0":
            try:
                num, den = rate.split("/")
                fps = round(float(num) / float(den), 2) if float(den) != 0 else None
            except (ValueError, ZeroDivisionError):
                fps = None
        if duration is None and video_stream.get("duration"):
            duration = float(video_stream["duration"])

    return {
        "duration_seconds": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "codec": codec,
    }


def generate_thumbnail(filepath: str, output_path: str, at_seconds: Optional[float] = None) -> bool:
    """Grabs a single frame as a JPEG thumbnail. Defaults to 10% into the clip."""
    seek_time = at_seconds
    if seek_time is None:
        try:
            meta = probe_video(filepath)
            duration = meta.get("duration_seconds") or 2.0
            seek_time = max(0.1, duration * 0.1)
        except Exception:
            seek_time = 1.0

    cmd = [
        "ffmpeg", "-y", "-ss", str(seek_time), "-i", filepath,
        "-frames:v", "1", "-q:v", "3", "-vf", "scale=320:-1",
        output_path,
    ]
    try:
        _run(cmd)
        return Path(output_path).exists()
    except (FFmpegNotFoundError, subprocess.CalledProcessError):
        return False


def extract_audio(filepath: str, output_wav_path: str) -> bool:
    """Extracts mono 16kHz audio track for Whisper transcription."""
    cmd = [
        "ffmpeg", "-y", "-i", filepath,
        "-vn", "-ac", "1", "-ar", "16000",
        output_wav_path,
    ]
    try:
        _run(cmd)
        return Path(output_wav_path).exists()
    except (FFmpegNotFoundError, subprocess.CalledProcessError):
        return False
