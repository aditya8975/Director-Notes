from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str = ""
    whisper_model_size: str = "base"  # tiny|base|small|medium|large-v3 (bigger = slower, more accurate)
    whisper_device: str = "cpu"  # "cpu" or "cuda" if you have an nvidia gpu
    whisper_compute_type: str = "int8"  # int8 is fastest on cpu

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
