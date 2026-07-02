from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Clip
from app.schemas import ChatRequest
from app.services.ai_chat import ask_about_project

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
def chat(body: ChatRequest, db: Session = Depends(get_db)):
    clips = db.query(Clip).all()
    if not clips:
        raise HTTPException(400, "No clips imported yet - import footage first")

    history = [{"role": m.role, "content": m.content} for m in body.history]

    try:
        answer = ask_about_project(clips, body.question, history)
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Chat request failed: {e}")

    return {"answer": answer}
