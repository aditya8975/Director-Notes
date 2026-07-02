"""
Local transcription using faster-whisper (a fast, CTranslate2-based
reimplementation of OpenAI Whisper that runs entirely on your machine,
no API key, no upload).

The model downloads once on first use (cached under ~/.cache/huggingface)
and then runs offline.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Iterator

from app.config import settings
from app.services.video_meta import extract_audio

_model = None


def _get_model():
    """Lazily load the whisper model once and reuse it across requests."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(
            settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    return _model


def transcribe_clip(filepath: str) -> list[dict]:
    """
    Runs the full transcription pipeline on a video file:
    1. Extract audio to a temp wav
    2. Run whisper over it
    3. Return a list of {start_time, end_time, text} segments

    Raises RuntimeError if ffmpeg or the model fails.
    """
    with tempfile.TemporaryDirectory() as tmp:
        wav_path = str(Path(tmp) / "audio.wav")
        ok = extract_audio(filepath, wav_path)
        if not ok:
            raise RuntimeError(
                "Could not extract audio from this clip. Check that ffmpeg is "
                "installed and the file is a valid video."
            )

        model = _get_model()
        segments, _info = model.transcribe(wav_path, beam_size=5, vad_filter=True)

        results = []
        for seg in segments:
            results.append({
                "start_time": round(seg.start, 2),
                "end_time": round(seg.end, 2),
                "text": seg.text.strip(),
            })
        return results
