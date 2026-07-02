from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
DB_DIR = STORAGE_DIR / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR = STORAGE_DIR / "clips"
CLIPS_DIR.mkdir(parents=True, exist_ok=True)
THUMBS_DIR = STORAGE_DIR / "thumbnails"
THUMBS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DB_DIR / "director.sqlite3"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
