import { useState, useRef, useEffect } from "react";
import { api } from "../lib/api.js";
import "../styles/chat.css";

// Parses [clip_id: abc123] and [clip_id: abc123, t: 42.5] references out of
// the AI's reply so we can render them as clickable jump-to-clip chips.
function parseReferences(text) {
  const parts = [];
  const regex = /\[clip_id:\s*([a-zA-Z0-9]+)(?:,\s*t:\s*([\d.]+))?\]/g;
  let lastIndex = 0;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: "text", value: text.slice(lastIndex, match.index) });
    }
    parts.push({ type: "ref", clipId: match[1], time: match[2] ? parseFloat(match[2]) : null });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push({ type: "text", value: text.slice(lastIndex) });
  }
  return parts;
}

function MessageContent({ content, clips, onJumpToClip }) {
  const parts = parseReferences(content);
  return (
    <span>
      {parts.map((p, i) => {
        if (p.type === "text") return <span key={i}>{p.value}</span>;
        const clip = clips.find((c) => c.id === p.clipId);
        return (
          <button
            key={i}
            className="ref-chip"
            onClick={() => onJumpToClip(p.clipId)}
            title={clip ? clip.filename : p.clipId}
          >
            ▶ {clip ? clip.filename : "clip"}
            {p.time != null ? ` @${p.time.toFixed(1)}s` : ""}
          </button>
        );
      })}
    </span>
  );
}

const SUGGESTIONS = [
  "What scenes have I covered so far?",
  "Which clips feature the most dialogue?",
  "Where does the pacing feel slow?",
  "Summarize what happens across all clips",
];

export default function ChatView({ clips, onJumpToClip }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  const send = async (question) => {
    const q = question.trim();
    if (!q || sending) return;
    setError(null);
    const nextMessages = [...messages, { role: "user", content: q }];
    setMessages(nextMessages);
    setInput("");
    setSending(true);
    try {
      const res = await api.chat(q, messages);
      setMessages([...nextMessages, { role: "assistant", content: res.answer }]);
    } catch (e) {
      setError(e.message);
    } finally {
      setSending(false);
    }
  };

  const noFootage = clips.length === 0;

  return (
    <div className="chat-view">
      <div className="chat-scroll" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="chat-empty">
            <div className="empty-glyph">◎</div>
            <h2>Ask about your project</h2>
            <p>
              Questions are answered using every clip's transcript, tags, and
              notes — processed via Groq, fast enough for back-and-forth while
              you're scrubbing through footage.
            </p>
            {!noFootage && (
              <div className="chat-suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`chat-msg chat-msg-${m.role}`}>
            <div className="chat-msg-role">{m.role === "user" ? "you" : "assistant"}</div>
            <div className="chat-msg-bubble">
              <MessageContent content={m.content} clips={clips} onJumpToClip={onJumpToClip} />
            </div>
          </div>
        ))}

        {sending && (
          <div className="chat-msg chat-msg-assistant">
            <div className="chat-msg-role">assistant</div>
            <div className="chat-msg-bubble chat-thinking">thinking…</div>
          </div>
        )}

        {error && <div className="chat-error">{error}</div>}
      </div>

      <form
        className="chat-input-row"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          type="text"
          placeholder={
            noFootage
              ? "Import some footage first…"
              : "Ask where a scene is, what's missing, how pacing feels…"
          }
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={noFootage}
        />
        <button type="submit" disabled={noFootage || sending || !input.trim()}>
          Ask
        </button>
      </form>
    </div>
  );
}
