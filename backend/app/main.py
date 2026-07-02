from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import clips, transcription, tags, mindmap, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Director's Footage Notebook API", lifespan=lifespan)

# Frontend runs on localhost:5173 (Vite default) during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clips.router)
app.include_router(transcription.router)
app.include_router(tags.router)
app.include_router(mindmap.router)
app.include_router(chat.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
