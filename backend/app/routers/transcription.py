from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Clip, TranscriptSegment
from app.services.transcription import transcribe_clip

router = APIRouter(prefix="/api/transcribe", tags=["transcription"])


@router.post("/{clip_id}")
def transcribe(clip_id: str, db: Session = Depends(get_db)):
    """
    Runs local Whisper transcription on a clip. This can take anywhere from a
    few seconds to a couple minutes depending on clip length and model size -
    the frontend should show a spinner and poll /api/clips/{id} for status.
    """
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(404, "Clip not found")

    clip.transcription_status = "running"
    db.commit()

    try:
        segments = transcribe_clip(clip.filepath)
    except Exception as e:
        clip.transcription_status = "error"
        clip.transcription_error = str(e)
        db.commit()
        raise HTTPException(500, f"Transcription failed: {e}")

    # Clear any previous segments (re-transcribe case) and insert fresh ones
    db.query(TranscriptSegment).filter(TranscriptSegment.clip_id == clip.id).delete()
    for seg in segments:
        db.add(TranscriptSegment(
            clip_id=clip.id,
            start_time=seg["start_time"],
            end_time=seg["end_time"],
            text=seg["text"],
        ))

    clip.transcribed = True
    clip.transcription_status = "done"
    clip.transcription_error = None
    db.commit()
    db.refresh(clip)
    return clip.to_dict(include_transcript=True)


@router.get("/{clip_id}")
def get_transcript(clip_id: str, db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(404, "Clip not found")
    return {
        "clip_id": clip.id,
        "status": clip.transcription_status,
        "segments": [s.to_dict() for s in clip.transcript_segments],
    }
