from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db, THUMBS_DIR
from app.models import Clip
from app.schemas import ImportFolderRequest, ClipNotesUpdate
from app.services.video_meta import (
    VIDEO_EXTENSIONS, probe_video, generate_thumbnail, FFmpegNotFoundError,
)

router = APIRouter(prefix="/api/clips", tags=["clips"])


@router.post("/import-folder")
def import_folder(req: ImportFolderRequest, db: Session = Depends(get_db)):
    """
    Scans a local folder for video files and registers each as a Clip.
    Does NOT copy files - clips stay wherever they are on disk; we just
    store the path. Metadata extraction happens as a follow-up step per clip
    (kept separate so a huge folder import doesn't block on ffprobe for all of them).
    """
    folder = Path(req.folder_path).expanduser()
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(400, f"Folder not found: {folder}")

    found = []
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
            found.append(path)

    if not found:
        raise HTTPException(400, "No video files found in that folder (looked for: "
                             + ", ".join(sorted(VIDEO_EXTENSIONS)) + ")")

    created, skipped = [], []
    for path in found:
        existing = db.query(Clip).filter(Clip.filepath == str(path)).first()
        if existing:
            skipped.append(existing.to_dict())
            continue
        clip = Clip(filename=path.name, filepath=str(path))
        db.add(clip)
        db.flush()
        created.append(clip.to_dict())

    db.commit()
    return {"imported": created, "already_existed": skipped, "total_found": len(found)}


@router.get("")
def list_clips(db: Session = Depends(get_db)):
    clips = db.query(Clip).order_by(Clip.imported_at.asc()).all()
    return [c.to_dict() for c in clips]


@router.get("/{clip_id}")
def get_clip(clip_id: str, db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(404, "Clip not found")
    return clip.to_dict(include_transcript=True)


@router.post("/{clip_id}/extract-metadata")
def extract_metadata(clip_id: str, db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(404, "Clip not found")

    try:
        meta = probe_video(clip.filepath)
    except FFmpegNotFoundError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to read video metadata: {e}")

    clip.duration_seconds = meta["duration_seconds"]
    clip.width = meta["width"]
    clip.height = meta["height"]
    clip.fps = meta["fps"]
    clip.codec = meta["codec"]
    clip.metadata_extracted = True

    thumb_path = THUMBS_DIR / f"{clip.id}.jpg"
    if generate_thumbnail(clip.filepath, str(thumb_path)):
        clip.thumbnail_path = str(thumb_path)

    db.commit()
    return clip.to_dict()


@router.post("/extract-metadata-all")
def extract_metadata_all(db: Session = Depends(get_db)):
    """Bulk-runs metadata extraction for every clip that hasn't had it run yet."""
    clips = db.query(Clip).filter(Clip.metadata_extracted == False).all()  # noqa: E712
    results = {"succeeded": 0, "failed": []}
    for clip in clips:
        try:
            meta = probe_video(clip.filepath)
            clip.duration_seconds = meta["duration_seconds"]
            clip.width = meta["width"]
            clip.height = meta["height"]
            clip.fps = meta["fps"]
            clip.codec = meta["codec"]
            clip.metadata_extracted = True
            thumb_path = THUMBS_DIR / f"{clip.id}.jpg"
            if generate_thumbnail(clip.filepath, str(thumb_path)):
                clip.thumbnail_path = str(thumb_path)
            results["succeeded"] += 1
        except Exception as e:
            results["failed"].append({"clip_id": clip.id, "error": str(e)})
    db.commit()
    return results


@router.get("/{clip_id}/thumbnail")
def get_thumbnail(clip_id: str, db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip or not clip.thumbnail_path or not Path(clip.thumbnail_path).exists():
        raise HTTPException(404, "Thumbnail not available")
    return FileResponse(clip.thumbnail_path, media_type="image/jpeg")


@router.get("/{clip_id}/video")
def stream_video(clip_id: str, db: Session = Depends(get_db)):
    """Streams the raw video file so the frontend <video> tag can play it directly."""
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip or not Path(clip.filepath).exists():
        raise HTTPException(404, "Video file not found on disk")
    return FileResponse(clip.filepath)


@router.patch("/{clip_id}/notes")
def update_notes(clip_id: str, body: ClipNotesUpdate, db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(404, "Clip not found")
    clip.notes = body.notes
    db.commit()
    return clip.to_dict()


@router.delete("/{clip_id}")
def delete_clip(clip_id: str, db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(404, "Clip not found")
    db.delete(clip)
    db.commit()
    return {"deleted": clip_id}
