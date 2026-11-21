from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    root: Path
    database_path: Path
    storage_dir: Path
    secret_key: str
    access_token_minutes: int
    tts_engine: str
    qwen_model_id: str
    qwen_clone_model_id: str
    qwen_speaker: str
    qwen_language: str
    qwen_instruct: str
    cors_origins: list[str]


def load_settings() -> Settings:
    root = Path(os.getenv("KRCV_ROOT", r"H:\KR_Cloud_Voice"))
    storage = Path(os.getenv("KRCV_STORAGE_DIR", str(root / "storage")))
    return Settings(
        root=root,
        database_path=root / "database" / "kr_cloud_voice.db",
        storage_dir=storage,
        secret_key=os.getenv("KRCV_SECRET_KEY", "development-only-change-me"),
        access_token_minutes=int(os.getenv("KRCV_ACCESS_TOKEN_MINUTES", "480")),
        tts_engine=os.getenv("KRCV_TTS_ENGINE", "mock"),
        qwen_model_id=os.getenv("KRCV_QWEN_MODEL_ID", "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"),
        qwen_clone_model_id=os.getenv("KRCV_QWEN_CLONE_MODEL_ID", "Qwen/Qwen3-TTS-12Hz-0.6B-Base"),
        qwen_speaker=os.getenv("KRCV_QWEN_SPEAKER", "Vivian"),
        qwen_language=os.getenv("KRCV_QWEN_LANGUAGE", "German"),
        qwen_instruct=os.getenv("KRCV_QWEN_INSTRUCT", ""),
        cors_origins=os.getenv("KRCV_CORS_ORIGINS", "http://127.0.0.1:5173").split(","),
    )
