const BASE_URL = "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // response wasn't JSON, fall back to statusText
    }
    throw new Error(detail);
  }
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return res.json();
  }
  return res;
}

export const api = {
  health: () => request("/api/health"),

  importFolder: (folderPath) =>
    request("/api/clips/import-folder", {
      method: "POST",
      body: JSON.stringify({ folder_path: folderPath }),
    }),

  listClips: () => request("/api/clips"),

  getClip: (clipId) => request(`/api/clips/${clipId}`),

  extractMetadata: (clipId) =>
    request(`/api/clips/${clipId}/extract-metadata`, { method: "POST" }),

  extractMetadataAll: () =>
    request("/api/clips/extract-metadata-all", { method: "POST" }),

  thumbnailUrl: (clipId) => `${BASE_URL}/api/clips/${clipId}/thumbnail`,
  videoUrl: (clipId) => `${BASE_URL}/api/clips/${clipId}/video`,

  updateNotes: (clipId, notes) =>
    request(`/api/clips/${clipId}/notes`, {
      method: "PATCH",
      body: JSON.stringify({ notes }),
    }),

  deleteClip: (clipId) => request(`/api/clips/${clipId}`, { method: "DELETE" }),

  transcribeClip: (clipId) =>
    request(`/api/transcribe/${clipId}`, { method: "POST" }),

  getTranscript: (clipId) => request(`/api/transcribe/${clipId}`),

  listTags: () => request("/api/tags"),

  createTag: (kind, value) =>
    request("/api/tags", {
      method: "POST",
      body: JSON.stringify({ kind, value }),
    }),

  deleteTag: (tagId) => request(`/api/tags/${tagId}`, { method: "DELETE" }),

  assignTag: (clipId, tagId) =>
    request("/api/tags/assign", {
      method: "POST",
      body: JSON.stringify({ clip_id: clipId, tag_id: tagId }),
    }),

  unassignTag: (clipId, tagId) =>
    request("/api/tags/unassign", {
      method: "POST",
      body: JSON.stringify({ clip_id: clipId, tag_id: tagId }),
    }),

  suggestTags: (clipId) =>
    request("/api/tags/suggest", {
      method: "POST",
      body: JSON.stringify({ clip_id: clipId }),
    }),

  getMindmap: () => request("/api/mindmap"),

  chat: (question, history) =>
    request("/api/chat", {
      method: "POST",
      body: JSON.stringify({ question, history }),
    }),
};
