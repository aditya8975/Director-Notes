"""
Lets the director ask natural-language questions about their footage:
"where's the scene where Maya finds the letter", "where does pacing slow down", etc.

How it works: every clip's transcript + tags gets flattened into a compact text
index. That whole index (it's small - transcripts are just text) gets sent to
Groq along with the question, and the model is asked to point back to specific
clip ids and timestamps it thinks are relevant, plus a plain-language answer.

This is intentionally simple (no vector DB) because a feature film's worth of
dialogue transcripts is still only a few hundred KB of text - well within a
single context window for a fast model like Groq's llama/gpt-oss models. If the
project grows huge later, swap this for a proper retrieval step.
"""
from __future__ import annotations

import json
from typing import Optional

from groq import Groq

from app.config import settings
from app.models import Clip

CHAT_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are an assistant embedded in a video editing tool for a film \
director. You have access to an index of every clip in the project: its filename, \
duration, tags (character / scene / camera angle), and full spoken transcript with \
timestamps.

The director will ask you things like "where is the scene where X happens", \
"which clips feature character Y", "where does the pacing feel slow", or \
"summarize what happens in act 2".

Answer conversationally and directly. When you reference a specific clip, ALWAYS \
include its clip_id in square brackets like [clip_id: abc123] so the app can link \
to it. If you reference a specific moment, include the timestamp in seconds too, \
like [clip_id: abc123, t: 42.5].

If the index doesn't contain enough information to answer confidently, say so \
plainly rather than guessing. Keep answers focused and skip filler preamble."""


def _build_index(clips: list[Clip]) -> str:
    lines = []
    for clip in clips:
        tags = [f"{ct.tag.kind.value}:{ct.tag.value}" for ct in clip.clip_tags]
        lines.append(f"--- CLIP [{clip.id}] {clip.filename} "
                      f"(duration: {clip.duration_seconds or '?'}s) ---")
        if tags:
            lines.append(f"tags: {', '.join(tags)}")
        if clip.notes:
            lines.append(f"director notes: {clip.notes}")
        if clip.transcript_segments:
            lines.append("transcript:")
            for seg in clip.transcript_segments:
                lines.append(f"  [{seg.start_time:.1f}s-{seg.end_time:.1f}s] {seg.text}")
        else:
            lines.append("transcript: (not yet transcribed)")
        lines.append("")
    return "\n".join(lines)


def ask_about_project(clips: list[Clip], question: str, chat_history: Optional[list[dict]] = None) -> str:
    if not settings.groq_api_key:
        raise RuntimeError(
            "No Groq API key configured. Add GROQ_API_KEY to backend/.env "
            "(get a free key at console.groq.com/keys)."
        )

    client = Groq(api_key=settings.groq_api_key)
    index_text = _build_index(clips)

    messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n\nPROJECT INDEX:\n" + index_text}]
    if chat_history:
        messages.extend(chat_history)
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def suggest_tags_for_transcript(transcript_text: str, existing_characters: list[str]) -> dict:
    """
    Optional helper (Phase 3+) - asks Groq to suggest likely character names
    mentioned/speaking in a transcript, as a starting point for manual tagging.
    Not run automatically; called only when the user clicks "suggest tags".
    """
    if not settings.groq_api_key:
        raise RuntimeError("No Groq API key configured.")

    client = Groq(api_key=settings.groq_api_key)
    prompt = f"""Given this scene transcript, suggest which characters from this \
known list appear to be speaking or present: {existing_characters or '(no known characters yet)'}

Also suggest a short scene name (3-6 words) describing what's happening.

Transcript:
{transcript_text}

Respond ONLY with JSON in this exact shape, nothing else:
{{"likely_characters": ["name1", "name2"], "suggested_scene_name": "short scene description"}}"""

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=256,
    )
    raw = response.choices[0].message.content.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"likely_characters": [], "suggested_scene_name": ""}
