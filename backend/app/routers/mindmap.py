from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Clip, TagKind

router = APIRouter(prefix="/api/mindmap", tags=["mindmap"])


@router.get("")
def get_mindmap(db: Session = Depends(get_db)):
    """
    Builds the mind map graph: every clip is a node, and an edge is drawn
    between two clips whenever they share a tag (same character, same scene,
    or same camera angle). Scene tags create the strongest grouping since
    that's the primary story structure; character and camera-angle shared
    tags create lighter cross-links.

    Returns nodes + edges in a shape the React Flow frontend can consume directly.
    """
    clips = db.query(Clip).all()

    nodes = []
    for clip in clips:
        tags = [ct.tag for ct in clip.clip_tags]
        nodes.append({
            "id": clip.id,
            "label": clip.filename,
            "duration_seconds": clip.duration_seconds,
            "thumbnail_path": clip.thumbnail_path,
            "transcribed": clip.transcribed,
            "tags": [t.to_dict() for t in tags],
            # primary scene tag drives clustering/coloring in the frontend layout
            "primary_scene": next((t.value for t in tags if t.kind == TagKind.scene), None),
        })

    # Map tag_id -> list of clip_ids that carry it, so we can connect every
    # pair of clips sharing that tag.
    tag_to_clips: dict[str, list[str]] = defaultdict(list)
    tag_lookup = {}
    for clip in clips:
        for ct in clip.clip_tags:
            tag_to_clips[ct.tag.id].append(clip.id)
            tag_lookup[ct.tag.id] = ct.tag

    edges = []
    seen_pairs = set()
    for tag_id, clip_ids in tag_to_clips.items():
        if len(clip_ids) < 2:
            continue
        tag = tag_lookup[tag_id]
        for i in range(len(clip_ids)):
            for j in range(i + 1, len(clip_ids)):
                a, b = sorted([clip_ids[i], clip_ids[j]])
                pair_key = (a, b, tag.kind.value)
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                edges.append({
                    "id": f"{a}-{b}-{tag.id}",
                    "source": a,
                    "target": b,
                    "via_tag_kind": tag.kind.value,
                    "via_tag_value": tag.value,
                })

    return {"nodes": nodes, "edges": edges}
