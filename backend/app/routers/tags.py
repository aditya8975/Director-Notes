from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Clip, Tag, ClipTag, TagKind
from app.schemas import TagCreate, ClipTagAssign, SuggestTagsRequest
from app.services.ai_chat import suggest_tags_for_transcript

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("")
def list_tags(db: Session = Depends(get_db)):
    tags = db.query(Tag).order_by(Tag.kind.asc(), Tag.value.asc()).all()
    return [t.to_dict() for t in tags]


@router.post("")
def create_tag(body: TagCreate, db: Session = Depends(get_db)):
    try:
        kind = TagKind(body.kind)
    except ValueError:
        raise HTTPException(400, f"Invalid tag kind: {body.kind}. Must be one of "
                             f"{[k.value for k in TagKind]}")

    value = body.value.strip()
    if not value:
        raise HTTPException(400, "Tag value cannot be empty")

    existing = db.query(Tag).filter(Tag.kind == kind, Tag.value == value).first()
    if existing:
        return existing.to_dict()

    tag = Tag(kind=kind, value=value)
    db.add(tag)
    db.commit()
    return tag.to_dict()


@router.delete("/{tag_id}")
def delete_tag(tag_id: str, db: Session = Depends(get_db)):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(404, "Tag not found")
    db.delete(tag)
    db.commit()
    return {"deleted": tag_id}


@router.post("/assign")
def assign_tag(body: ClipTagAssign, db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == body.clip_id).first()
    tag = db.query(Tag).filter(Tag.id == body.tag_id).first()
    if not clip:
        raise HTTPException(404, "Clip not found")
    if not tag:
        raise HTTPException(404, "Tag not found")

    existing = db.query(ClipTag).filter(
        ClipTag.clip_id == clip.id, ClipTag.tag_id == tag.id
    ).first()
    if existing:
        return clip.to_dict()

    db.add(ClipTag(clip_id=clip.id, tag_id=tag.id))
    db.commit()
    db.refresh(clip)
    return clip.to_dict()


@router.post("/unassign")
def unassign_tag(body: ClipTagAssign, db: Session = Depends(get_db)):
    link = db.query(ClipTag).filter(
        ClipTag.clip_id == body.clip_id, ClipTag.tag_id == body.tag_id
    ).first()
    if link:
        db.delete(link)
        db.commit()
    clip = db.query(Clip).filter(Clip.id == body.clip_id).first()
    return clip.to_dict() if clip else {"ok": True}


@router.post("/suggest")
def suggest_tags(body: SuggestTagsRequest, db: Session = Depends(get_db)):
    """AI-assisted tag suggestion (Phase 3+ helper) - suggests likely characters
    and a scene name from a clip's transcript. Director still confirms/applies."""
    clip = db.query(Clip).filter(Clip.id == body.clip_id).first()
    if not clip:
        raise HTTPException(404, "Clip not found")
    if not clip.transcript_segments:
        raise HTTPException(400, "Clip has no transcript yet - transcribe it first")

    transcript_text = "\n".join(s.text for s in clip.transcript_segments)
    known_characters = [
        t.value for t in db.query(Tag).filter(Tag.kind == TagKind.character).all()
    ]

    try:
        suggestion = suggest_tags_for_transcript(transcript_text, known_characters)
    except Exception as e:
        raise HTTPException(500, str(e))

    return suggestion
