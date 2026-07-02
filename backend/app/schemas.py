from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ImportFolderRequest(BaseModel):
    folder_path: str


class ClipNotesUpdate(BaseModel):
    notes: Optional[str] = None


class TagCreate(BaseModel):
    kind: str  # character|scene|camera_angle|custom
    value: str


class ClipTagAssign(BaseModel):
    clip_id: str
    tag_id: str


class ChatMessage(BaseModel):
    role: str  # user|assistant
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[ChatMessage] = []


class SuggestTagsRequest(BaseModel):
    clip_id: str
