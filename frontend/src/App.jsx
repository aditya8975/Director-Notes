import { useState, useEffect, useCallback } from "react";
import { api } from "./lib/api.js";
import BinView from "./components/BinView.jsx";
import MindMapView from "./components/MindMapView.jsx";
import ChatView from "./components/ChatView.jsx";
import ClipDetailDrawer from "./components/ClipDetailDrawer.jsx";
import "./styles/app.css";

const VIEWS = [
  { id: "bin", label: "Bin", glyph: "▦" },
  { id: "mindmap", label: "Mind Map", glyph: "◈" },
  { id: "chat", label: "Ask", glyph: "◎" },
];

export default function App() {
  const [view, setView] = useState("bin");
  const [clips, setClips] = useState([]);
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [backendOk, setBackendOk] = useState(null);
  const [selectedClipId, setSelectedClipId] = useState(null);

  const refreshClips = useCallback(async () => {
    try {
      const data = await api.listClips();
      setClips(data);
    } catch (e) {
      console.error("Failed to load clips", e);
    }
  }, []);

  const refreshTags = useCallback(async () => {
    try {
      const data = await api.listTags();
      setTags(data);
    } catch (e) {
      console.error("Failed to load tags", e);
    }
  }, []);

  useEffect(() => {
    api
      .health()
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false));
  }, []);

  useEffect(() => {
    if (backendOk) {
      Promise.all([refreshClips(), refreshTags()]).finally(() => setLoading(false));
    }
  }, [backendOk, refreshClips, refreshTags]);

  if (backendOk === false) {
    return (
      <div className="backend-down">
        <div className="backend-down-card">
          <div className="rec-dot" />
          <h1>Backend not reachable</h1>
          <p>
            The app couldn't reach the local server at <code>localhost:8000</code>.
            Make sure it's running:
          </p>
          <pre>cd backend{"\n"}uvicorn app.main:app --reload</pre>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="rec-dot" />
          <div>
            <div className="brand-name">Footage Notebook</div>
            <div className="brand-sub">for directors</div>
          </div>
        </div>

        <nav className="nav">
          {VIEWS.map((v) => (
            <button
              key={v.id}
              className={`nav-item ${view === v.id ? "active" : ""}`}
              onClick={() => setView(v.id)}
            >
              <span className="nav-glyph">{v.glyph}</span>
              {v.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-stats">
          <div className="stat-row">
            <span>clips</span>
            <span className="mono">{clips.length}</span>
          </div>
          <div className="stat-row">
            <span>transcribed</span>
            <span className="mono">{clips.filter((c) => c.transcribed).length}</span>
          </div>
          <div className="stat-row">
            <span>tags</span>
            <span className="mono">{tags.length}</span>
          </div>
        </div>
      </aside>

      <main className="main-area">
        {loading ? (
          <div className="loading-state">Loading project…</div>
        ) : view === "bin" ? (
          <BinView
            clips={clips}
            tags={tags}
            refreshClips={refreshClips}
            refreshTags={refreshTags}
            onSelectClip={setSelectedClipId}
          />
        ) : view === "mindmap" ? (
          <MindMapView onSelectClip={setSelectedClipId} />
        ) : (
          <ChatView clips={clips} onJumpToClip={setSelectedClipId} />
        )}
      </main>

      {selectedClipId && (
        <ClipDetailDrawer
          clipId={selectedClipId}
          tags={tags}
          onClose={() => setSelectedClipId(null)}
          onChanged={refreshClips}
          refreshTags={refreshTags}
        />
      )}
    </div>
  );
}
