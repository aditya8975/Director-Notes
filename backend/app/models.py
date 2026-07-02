"""
Database models.

Core entities:
- Clip: one video file imported into a project. Holds metadata + status flags.
- TranscriptSegment: one timestamped chunk of speech-to-text for a clip.
- Tag: a label applied to a clip - has a `kind` (character / scene / camera_angle / custom)
  and a `value` (the actual name, e.g. "Maya", "Kitchen confrontation", "Close-up").
  Color is derived from kind+value so the same tag always renders the same color.
- ClipTag: many-to-many join between Clip and Tag, optionally scoped to a time range
  within the clip (so a tag can apply to just part of a clip later, even though v1
  applies tags to the whole clip).
"""
from __future__ import annotations

import datetime as dt
import enum
import uuid

from sqlalchemy import (
    Column, String, Float, Integer, Boolean, ForeignKey, DateTime, Text, Enum as SAEnum
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def gen_id() -> str:
    return uuid.uuid4().hex[:12]


class TagKind(str, enum.Enum):
    character = "character"
    scene = "scene"
    camera_angle = "camera_angle"
    custom = "custom"


# Fixed color assignment per tag kind, so the UI legend is predictable.
# Individual tag *values* within a kind get a consistent hash-based shade.
TAG_KIND_COLORS = {
    TagKind.character: "coral",
    TagKind.scene: "gray",
    TagKind.camera_angle: "teal",
    TagKind.custom: "purple",
}


class Clip(Base):
    __tablename__ = "clips"

    id = Column(String, primary_key=True, default=gen_id)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False, unique=True)
    duration_seconds = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    fps = Column(Float, nullable=True)
    codec = Column(String, nullable=True)
    thumbnail_path = Column(String, nullable=True)
    imported_at = Column(DateTime, default=dt.datetime.utcnow)

    # Pipeline status flags
    metadata_extracted = Column(Boolean, default=False)
    transcribed = Column(Boolean, default=False)
    transcription_status = Column(String, default="pending")  # pending|running|done|error
    transcription_error = Column(Text, nullable=True)

    # Free-form notes a director might jot for this clip
    notes = Column(Text, nullable=True)

    transcript_segments = relationship(
        "TranscriptSegment", back_populates="clip", cascade="all, delete-orphan",
        order_by="TranscriptSegment.start_time",
    )
    clip_tags = relationship("ClipTag", back_populates="clip", cascade="all, delete-orphan")

    def to_dict(self, include_transcript: bool = False, include_tags: bool = True):
        d = {
            "id": self.id,
            "filename": self.filename,
            "filepath": self.filepath,
            "duration_seconds": self.duration_seconds,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "codec": self.codec,
            "thumbnail_path": self.thumbnail_path,
            "imported_at": self.imported_at.isoformat() if self.imported_at else None,
            "metadata_extracted": self.metadata_extracted,
            "transcribed": self.transcribed,
            "transcription_status": self.transcription_status,
            "transcription_error": self.transcription_error,
            "notes": self.notes,
        }
        if include_transcript:
            d["transcript_segments"] = [s.to_dict() for s in self.transcript_segments]
        if include_tags:
            d["tags"] = [ct.tag.to_dict() for ct in self.clip_tags]
        return d


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id = Column(String, primary_key=True, default=gen_id)
    clip_id = Column(String, ForeignKey("clips.id"), nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)

    clip = relationship("Clip", back_populates="transcript_segments")

    def to_dict(self):
        return {
            "id": self.id,
            "clip_id": self.clip_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text,
        }


class Tag(Base):
    __tablename__ = "tags"

    id = Column(String, primary_key=True, default=gen_id)
    kind = Column(SAEnum(TagKind), nullable=False)
    value = Column(String, nullable=False)

    clip_tags = relationship("ClipTag", back_populates="tag", cascade="all, delete-orphan")

    def color_ramp(self) -> str:
        return TAG_KIND_COLORS.get(self.kind, "gray")

    def to_dict(self):
        return {
            "id": self.id,
            "kind": self.kind.value if isinstance(self.kind, TagKind) else self.kind,
            "value": self.value,
            "color_ramp": self.color_ramp(),
        }


class ClipTag(Base):
    __tablename__ = "clip_tags"

    id = Column(String, primary_key=True, default=gen_id)
    clip_id = Column(String, ForeignKey("clips.id"), nullable=False)
    tag_id = Column(String, ForeignKey("tags.id"), nullable=False)

    clip = relationship("Clip", back_populates="clip_tags")
    tag = relationship("Tag", back_populates="clip_tags")
