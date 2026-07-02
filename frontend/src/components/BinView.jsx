import { useState, useMemo } from "react";
import { api } from "../lib/api.js";
import TagPill from "./TagPill.jsx";
import "../styles/binview.css";

function formatDuration(seconds) {
  if (seconds == null) return "—:—";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function StatusChip({ clip }) {
  if (clip.transcription_status === "running") {
    return <span className="status-chip status-running">transcribing…</span>;
  }
  if (clip.transcription_status === "error") {
    return <span className="status-chip status-error">transcribe failed</span>;
  }
  if (clip.transcribed) {
    return <span className="status-chip status-done">transcribed</span>;
  }
  if (!clip.metadata_extracted) {
    return <span className="status-chip status-pending">no metadata</span>;
  }
  return <span className="status-chip status-pending">not transcribed</span>;
}

export default function BinView({ clips, tags, refreshClips, refreshTags, onSelectClip }) {
  const [folderPath, setFolderPath] = useState("");
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState(null);
  const [activeFilter, setActiveFilter] = useState(null); // tag id
  const [bulkRunning, setBulkRunning] = useState(false);

  const handleImport = async (e) => {
    e.preventDefault();
    if (!folderPath.trim()) return;
    setImporting(true);
    setImportError(null);
    try {
      await api.importFolder(folderPath.trim());
      await refreshClips();
      setFolderPath("");
    } catch (err) {
      setImportError(err.message);
    } finally {
      setImporting(false);
    }
  };

  const handleExtractAll = async () => {
    setBulkRunning(true);
    try {
      await api.extractMetadataAll();
      await refreshClips();
    } finally {
      setBulkRunning(false);
    }
  };

  const filteredClips = useMemo(() => {
    if (!activeFilter) return clips;
    return clips.filter((c) => c.tags?.some((t) => t.id === activeFilter));
  }, [clips, activeFilter]);

  const pendingMetadata = clips.filter((c) => !c.metadata_extracted).length;

  return (
    <div className="bin-view">
      <header className="bin-header">
        <div>
          <h1>Bin</h1>
          <p className="bin-sub">Every clip imported into this project, in one place.</p>
        </div>
        <form className="import-form" onSubmit={handleImport}>
          <input
            type="text"
            placeholder="/Users/you/Footage/Day3"
            value={folderPath}
            onChange={(e) => setFolderPath(e.target.value)}
          />
          <button type="submit" disabled={importing}>
            {importing ? "Scanning…" : "Import folder"}
          </button>
        </form>
      </header>

      {importError && <div className="banner banner-error">{importError}</div>}

      {pendingMetadata > 0 && (
        <div className="banner banner-info">
          <span>{pendingMetadata} clip{pendingMetadata !== 1 ? "s" : ""} missing metadata/thumbnail.</span>
          <button onClick={handleExtractAll} disabled={bulkRunning}>
            {bulkRunning ? "Reading…" : "Read metadata for all"}
          </button>
        </div>
      )}

      {tags.length > 0 && (
        <div className="filter-row">
          <span className="filter-label">filter:</span>
          <button
            className={`filter-chip ${activeFilter === null ? "active" : ""}`}
            onClick={() => setActiveFilter(null)}
          >
            all
          </button>
          {tags.map((t) => (
            <button
              key={t.id}
              className={`filter-chip ${activeFilter === t.id ? "active" : ""}`}
              style={{ "--chip-color": `var(--tag-${t.kind})` }}
              onClick={() => setActiveFilter(activeFilter === t.id ? null : t.id)}
            >
              {t.value}
            </button>
          ))}
        </div>
      )}

      {clips.length === 0 ? (
        <div className="empty-state">
          <div className="empty-glyph">▦</div>
          <h2>No footage yet</h2>
          <p>
            Paste the full path to a folder of clips above and import it.
            Files stay where they are — nothing gets copied or uploaded.
          </p>
        </div>
      ) : (
        <div className="clip-grid">
          {filteredClips.map((clip) => (
            <button
              key={clip.id}
              className="clip-card"
              onClick={() => onSelectClip(clip.id)}
            >
              <div className="clip-thumb">
                {clip.thumbnail_path ? (
                  <img src={api.thumbnailUrl(clip.id)} alt="" loading="lazy" />
                ) : (
                  <div className="clip-thumb-placeholder">no preview</div>
                )}
                <span className="clip-duration mono">{formatDuration(clip.duration_seconds)}</span>
              </div>
              <div className="clip-meta">
                <div className="clip-filename" title={clip.filename}>
                  {clip.filename}
                </div>
                <div className="clip-tags">
                  {clip.tags?.slice(0, 3).map((t) => (
                    <TagPill key={t.id} tag={t} size="xs" />
                  ))}
                  {clip.tags?.length > 3 && (
                    <span className="tag-overflow">+{clip.tags.length - 3}</span>
                  )}
                </div>
                <StatusChip clip={clip} />
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
