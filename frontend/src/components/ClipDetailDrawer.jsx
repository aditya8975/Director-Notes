import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "../lib/api.js";
import TagPill from "./TagPill.jsx";
import "../styles/drawer.css";

const TAG_KINDS = [
  { id: "character", label: "Character" },
  { id: "scene", label: "Scene" },
  { id: "camera_angle", label: "Camera angle" },
  { id: "custom", label: "Custom" },
];

export default function ClipDetailDrawer({ clipId, tags, onClose, onChanged, refreshTags }) {
  const [clip, setClip] = useState(null);
  const [loading, setLoading] = useState(true);
  const [transcribing, setTranscribing] = useState(false);
  const [notesValue, setNotesValue] = useState("");
  const [savingNotes, setSavingNotes] = useState(false);
  const [newTagKind, setNewTagKind] = useState("character");
  const [newTagValue, setNewTagValue] = useState("");
  const [suggestion, setSuggestion] = useState(null);
  const [suggesting, setSuggesting] = useState(false);
  const [error, setError] = useState(null);
  const videoRef = useRef(null);
  const notesTimer = useRef(null);

  const loadClip = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getClip(clipId);
      setClip(data);
      setNotesValue(data.notes || "");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [clipId]);

  useEffect(() => {
    loadClip();
    setSuggestion(null);
    setError(null);
  }, [clipId, loadClip]);

  const handleTranscribe = async () => {
    setTranscribing(true);
    setError(null);
    try {
      const updated = await api.transcribeClip(clipId);
      setClip(updated);
      onChanged?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setTranscribing(false);
    }
  };

  const handleNotesChange = (val) => {
    setNotesValue(val);
    clearTimeout(notesTimer.current);
    setSavingNotes(true);
    notesTimer.current = setTimeout(async () => {
      try {
        await api.updateNotes(clipId, val);
      } finally {
        setSavingNotes(false);
      }
    }, 600);
  };

  const seekTo = (seconds) => {
    if (videoRef.current) {
      videoRef.current.currentTime = seconds;
      videoRef.current.play();
    }
  };

  const handleAddTag = async () => {
    if (!newTagValue.trim()) return;
    const tag = await api.createTag(newTagKind, newTagValue.trim());
    await api.assignTag(clipId, tag.id);
    setNewTagValue("");
    await Promise.all([loadClip(), refreshTags?.(), onChanged?.()]);
  };

  const handleApplyExistingTag = async (tagId) => {
    await api.assignTag(clipId, tagId);
    await Promise.all([loadClip(), onChanged?.()]);
  };

  const handleRemoveTag = async (tag) => {
    await api.unassignTag(clipId, tag.id);
    await Promise.all([loadClip(), onChanged?.()]);
  };

  const handleSuggest = async () => {
    setSuggesting(true);
    setError(null);
    try {
      const result = await api.suggestTags(clipId);
      setSuggestion(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setSuggesting(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Remove "${clip.filename}" from the project? The file on disk is untouched.`)) return;
    await api.deleteClip(clipId);
    onChanged?.();
    onClose();
  };

  const appliedTagIds = new Set((clip?.tags || []).map((t) => t.id));
  const availableExistingTags = tags.filter((t) => !appliedTagIds.has(t.id));

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <button className="drawer-close" onClick={onClose} aria-label="Close">
          ×
        </button>

        {loading || !clip ? (
          <div className="drawer-loading">Loading clip…</div>
        ) : (
          <>
            <div className="drawer-video-wrap">
              <video ref={videoRef} controls src={api.videoUrl(clipId)} />
            </div>

            <div className="drawer-body">
              <h2 className="drawer-title">{clip.filename}</h2>
              <div className="drawer-meta-row mono">
                {clip.width && clip.height ? `${clip.width}×${clip.height}` : "—"} ·{" "}
                {clip.fps ? `${clip.fps}fps` : "—"} ·{" "}
                {clip.codec || "—"} ·{" "}
                {clip.duration_seconds ? `${clip.duration_seconds.toFixed(1)}s` : "—"}
              </div>

              {error && <div className="drawer-error">{error}</div>}

              <section className="drawer-section">
                <div className="drawer-section-head">
                  <h3>Tags</h3>
                </div>
                <div className="applied-tags">
                  {clip.tags?.length ? (
                    clip.tags.map((t) => (
                      <TagPill key={t.id} tag={t} onRemove={handleRemoveTag} />
                    ))
                  ) : (
                    <span className="muted">No tags yet</span>
                  )}
                </div>

                <div className="tag-add-row">
                  <select value={newTagKind} onChange={(e) => setNewTagKind(e.target.value)}>
                    {TAG_KINDS.map((k) => (
                      <option key={k.id} value={k.id}>
                        {k.label}
                      </option>
                    ))}
                  </select>
                  <input
                    type="text"
                    placeholder="e.g. Maya, Kitchen, Close-up"
                    value={newTagValue}
                    onChange={(e) => setNewTagValue(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAddTag()}
                  />
                  <button onClick={handleAddTag}>Add</button>
                </div>

                {availableExistingTags.length > 0 && (
                  <div className="existing-tags-row">
                    <span className="muted-label">quick add:</span>
                    {availableExistingTags.slice(0, 8).map((t) => (
                      <button
                        key={t.id}
                        className="quick-tag-btn"
                        style={{ "--pill-color": `var(--tag-${t.kind})`, "--pill-color-dim": `var(--tag-${t.kind}-dim)` }}
                        onClick={() => handleApplyExistingTag(t.id)}
                      >
                        + {t.value}
                      </button>
                    ))}
                  </div>
                )}

                <button className="suggest-btn" onClick={handleSuggest} disabled={suggesting || !clip.transcribed}>
                  {suggesting ? "Asking AI…" : "Suggest tags from transcript (AI)"}
                </button>
                {!clip.transcribed && (
                  <p className="hint">Transcribe this clip first so the AI has something to read.</p>
                )}
                {suggestion && (
                  <div className="suggestion-box">
                    <div>
                      <strong>Likely characters:</strong>{" "}
                      {suggestion.likely_characters?.length
                        ? suggestion.likely_characters.join(", ")
                        : "none detected"}
                    </div>
                    {suggestion.suggested_scene_name && (
                      <div>
                        <strong>Suggested scene name:</strong> {suggestion.suggested_scene_name}
                      </div>
                    )}
                  </div>
                )}
              </section>

              <section className="drawer-section">
                <div className="drawer-section-head">
                  <h3>Transcript</h3>
                  <button
                    className="transcribe-btn"
                    onClick={handleTranscribe}
                    disabled={transcribing}
                  >
                    {transcribing
                      ? "Transcribing… (this can take a minute)"
                      : clip.transcribed
                      ? "Re-transcribe"
                      : "Transcribe with Whisper"}
                  </button>
                </div>

                {clip.transcript_segments?.length ? (
                  <div className="transcript-list">
                    {clip.transcript_segments.map((seg) => (
                      <button
                        key={seg.id}
                        className="transcript-row"
                        onClick={() => seekTo(seg.start_time)}
                      >
                        <span className="transcript-time mono">
                          {seg.start_time.toFixed(1)}s
                        </span>
                        <span className="transcript-text">{seg.text}</span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="muted">
                    {clip.transcription_status === "error"
                      ? `Transcription failed: ${clip.transcription_error}`
                      : "Not transcribed yet."}
                  </p>
                )}
              </section>

              <section className="drawer-section">
                <h3>Director's notes</h3>
                <textarea
                  value={notesValue}
                  onChange={(e) => handleNotesChange(e.target.value)}
                  placeholder="e.g. good take but boom shadow visible top-left, use audio only…"
                  rows={4}
                />
                {savingNotes && <span className="muted small">saving…</span>}
              </section>

              <button className="delete-btn" onClick={handleDelete}>
                Remove from project
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
