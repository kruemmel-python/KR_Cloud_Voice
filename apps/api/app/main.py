from __future__ import annotations

import asyncio
import json
import queue
import sys
import threading
import uuid
import wave
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

ROOT = Path(__file__).resolve().parents[3]
sys.path.extend([str(ROOT / "services" / "segmenter"), str(ROOT / "services" / "tts_worker")])
from mock_worker import synthesize  # noqa: E402
from segmenter import segment_text  # noqa: E402
from .db import Database
from .security import create_token, decode_token, hash_password, verify_password
from .settings import Settings, load_settings

settings: Settings = load_settings()
db = Database(settings.database_path)
bearer = HTTPBearer()
app = FastAPI(title="KR Cloud Voice API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
SUPPORTED_SPEAKERS = ("Vivian", "Serena", "Uncle_Fu", "Ryan", "Aiden", "Ono_Anna", "Sohee", "Eric", "Dylan")
generation_queue: queue.PriorityQueue[tuple[int, int, str, str, str, str]] = queue.PriorityQueue()
generation_sequence = 0
generation_sequence_lock = threading.Lock()


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


class ProjectIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class GenerationIn(BaseModel):
    segment_id: str
    priority: int = Field(default=10, ge=0, le=100)
    speaker: str | None = None


class ProjectGenerationIn(BaseModel):
    speaker: str | None = None


class VoiceProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


def now() -> str:
    return datetime.now(UTC).isoformat()


def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    return decode_token(credentials.credentials, settings)


@app.on_event("startup")
def initialize() -> None:
    db.initialize()
    for directory in (settings.storage_dir / "documents", settings.storage_dir / "segments", settings.storage_dir / "exports"):
        directory.mkdir(parents=True, exist_ok=True)
    # The in-memory priority queue is empty after an API restart. Restore jobs
    # from SQLite, including the chosen voice, before starting the worker.
    with db.connection() as con:
        con.execute("UPDATE generation_jobs SET status = 'queued', finished_at = NULL WHERE status = 'running'")
        con.execute("UPDATE text_segments SET status = 'queued' WHERE id IN (SELECT segment_id FROM generation_jobs WHERE status = 'queued')")
        queued_jobs = con.execute("SELECT id, segment_id, tenant_id, priority, speaker FROM generation_jobs WHERE status = 'queued' ORDER BY priority DESC, created_at ASC").fetchall()
    global generation_sequence
    with generation_sequence_lock:
        for job in queued_jobs:
            generation_sequence += 1
            speaker = job["speaker"] or settings.qwen_speaker
            generation_queue.put((-job["priority"], generation_sequence, job["id"], job["segment_id"], job["tenant_id"], speaker))
    threading.Thread(target=run_generation_worker, name="kr-cloud-voice-tts", daemon=True).start()


@app.get("/health")
def health():
    return {"status": "ok", "tts_engine": settings.tts_engine}


@app.get("/api/v1/voices")
def list_voices(user_id: str = Depends(current_user)):
    return {"voices": SUPPORTED_SPEAKERS, "default": settings.qwen_speaker}


@app.get("/api/v1/voice-profiles")
def list_voice_profiles(user_id: str = Depends(current_user)):
    with db.connection() as con:
        rows = con.execute("SELECT id, name, duration_seconds, created_at FROM voice_profiles WHERE tenant_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/v1/voice-profiles", status_code=201)
async def create_voice_profile(
    name: str = Form(...),
    reference_text: str = Form(...),
    consent: bool = Form(...),
    audio: UploadFile = File(...),
    user_id: str = Depends(current_user),
):
    """Store an explicitly consented, quality-checked recording for the owner's voice only."""
    if not consent:
        raise HTTPException(status_code=422, detail="Die Einwilligung zur Nutzung der eigenen Stimme ist erforderlich")
    if not name.strip() or not reference_text.strip():
        raise HTTPException(status_code=422, detail="Name und vorgelesener Referenztext sind erforderlich")
    if Path(audio.filename or "").suffix.lower() != ".wav":
        raise HTTPException(status_code=415, detail="Die Aufnahme muss im WAV-Format vorliegen")
    payload = await audio.read()
    if not payload or len(payload) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Die WAV-Aufnahme darf höchstens 10 MB groß sein")
    profile_id = str(uuid.uuid4())
    target = settings.storage_dir / "voices" / user_id / f"{profile_id}.wav"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    try:
        with wave.open(str(target), "rb") as recording:
            channels, sample_width, sample_rate, frames = recording.getnchannels(), recording.getsampwidth(), recording.getframerate(), recording.getnframes()
        duration = frames / sample_rate if sample_rate else 0
    except (wave.Error, EOFError) as exc:
        remove_owned_file(str(target))
        raise HTTPException(status_code=422, detail="Die Aufnahme ist keine lesbare PCM-WAV-Datei") from exc
    if channels != 1 or sample_width not in {2, 3, 4} or sample_rate < 16000 or not 10 <= duration <= 120:
        remove_owned_file(str(target))
        raise HTTPException(status_code=422, detail="Aufnahme-Regeln: Mono, mindestens 16 kHz und 10 bis 120 Sekunden")
    with db.connection() as con:
        con.execute("INSERT INTO voice_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (profile_id, user_id, name.strip(), str(target), reference_text.strip(), duration, now(), now()))
    return {"id": profile_id, "name": name.strip(), "duration_seconds": duration}


@app.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED)
def register(data: Credentials):
    user_id = str(uuid.uuid4())
    try:
        with db.connection() as con:
            con.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user_id, data.email.lower(), hash_password(data.password), now()))
    except Exception as exc:
        raise HTTPException(status_code=409, detail="E-Mail-Adresse ist bereits registriert") from exc
    return {"access_token": create_token(user_id, settings), "token_type": "bearer"}


@app.post("/api/v1/auth/login")
def login(data: Credentials):
    with db.connection() as con:
        row = con.execute("SELECT id, password_hash FROM users WHERE email = ?", (data.email.lower(),)).fetchone()
    if not row or not verify_password(data.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="E-Mail oder Passwort nicht korrekt")
    return {"access_token": create_token(row["id"], settings), "token_type": "bearer"}


@app.get("/api/v1/projects")
def list_projects(user_id: str = Depends(current_user)):
    with db.connection() as con:
        rows = con.execute("SELECT id, title, created_at FROM projects WHERE tenant_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/v1/projects", status_code=201)
def create_project(data: ProjectIn, user_id: str = Depends(current_user)):
    project_id = str(uuid.uuid4())
    with db.connection() as con:
        con.execute("INSERT INTO projects VALUES (?, ?, ?, ?)", (project_id, user_id, data.title.strip(), now()))
    return {"id": project_id, "title": data.title.strip()}


def remove_owned_file(path_value: str | None) -> None:
    """Remove a stored artifact only when it belongs to this application's storage."""
    if not path_value:
        return
    try:
        path = Path(path_value).resolve()
        storage = settings.storage_dir.resolve()
        if path.is_relative_to(storage) and path.is_file():
            path.unlink()
    except OSError:
        # A missing or locked artifact must not prevent database cleanup.
        pass


@app.delete("/api/v1/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, user_id: str = Depends(current_user)):
    with db.connection() as con:
        project = con.execute("SELECT id FROM projects WHERE id = ? AND tenant_id = ?", (project_id, user_id)).fetchone()
        if not project:
            raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
        audio_rows = con.execute("SELECT audio_path FROM text_segments WHERE project_id = ? AND tenant_id = ?", (project_id, user_id)).fetchall()
        document_rows = con.execute("SELECT stored_path FROM documents WHERE project_id = ? AND tenant_id = ?", (project_id, user_id)).fetchall()
        con.execute("DELETE FROM generation_jobs WHERE segment_id IN (SELECT id FROM text_segments WHERE project_id = ? AND tenant_id = ?)", (project_id, user_id))
        con.execute("DELETE FROM text_segments WHERE project_id = ? AND tenant_id = ?", (project_id, user_id))
        con.execute("DELETE FROM documents WHERE project_id = ? AND tenant_id = ?", (project_id, user_id))
        con.execute("DELETE FROM projects WHERE id = ? AND tenant_id = ?", (project_id, user_id))
    for row in audio_rows:
        remove_owned_file(row["audio_path"])
    for row in document_rows:
        remove_owned_file(row["stored_path"])
    remove_owned_file(str(settings.storage_dir / "exports" / user_id / f"{project_id}.zip"))


@app.delete("/api/v1/segments/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_segment(segment_id: str, user_id: str = Depends(current_user)):
    with db.connection() as con:
        segment = con.execute("SELECT audio_path FROM text_segments WHERE id = ? AND tenant_id = ?", (segment_id, user_id)).fetchone()
        if not segment:
            raise HTTPException(status_code=404, detail="Titel nicht gefunden")
        con.execute("DELETE FROM generation_jobs WHERE segment_id = ? AND tenant_id = ?", (segment_id, user_id))
        con.execute("DELETE FROM text_segments WHERE id = ? AND tenant_id = ?", (segment_id, user_id))
    remove_owned_file(segment["audio_path"])


@app.delete("/api/v1/voice-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_voice_profile(profile_id: str, user_id: str = Depends(current_user)):
    with db.connection() as con:
        profile = con.execute("SELECT audio_path FROM voice_profiles WHERE id = ? AND tenant_id = ?", (profile_id, user_id)).fetchone()
        if not profile:
            raise HTTPException(status_code=404, detail="Stimmprofil nicht gefunden")
        con.execute("DELETE FROM voice_profiles WHERE id = ? AND tenant_id = ?", (profile_id, user_id))
    remove_owned_file(profile["audio_path"])


@app.post("/api/v1/documents", status_code=201)
async def upload_document(project_id: str = Form(...), file: UploadFile = File(...), user_id: str = Depends(current_user)):
    if Path(file.filename or "").suffix.lower() not in {".txt", ".md"}:
        raise HTTPException(status_code=415, detail="V1 akzeptiert TXT und Markdown. EPUB/PDF/DOCX folgen über Parser-Adapter.")
    with db.connection() as con:
        project = con.execute("SELECT id FROM projects WHERE id = ? AND tenant_id = ?", (project_id, user_id)).fetchone()
    if not project:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    body = await file.read()
    if len(body) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Maximale Uploadgröße: 10 MB")
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="Datei muss UTF-8-kodiert sein") from exc
    document_id = str(uuid.uuid4())
    stored = settings.storage_dir / "documents" / user_id / f"{document_id}{Path(file.filename).suffix.lower()}"
    stored.parent.mkdir(parents=True, exist_ok=True)
    stored.write_bytes(body)
    pieces = segment_text(text)
    with db.connection() as con:
        con.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?)", (document_id, user_id, project_id, file.filename, file.content_type or "text/plain", str(stored), now()))
        for ordinal, (chapter, piece) in enumerate(pieces, 1):
            con.execute("INSERT INTO text_segments (id,tenant_id,project_id,document_id,chapter,ordinal,original_text,normalized_text,created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (str(uuid.uuid4()), user_id, project_id, document_id, chapter, ordinal, piece, piece, now()))
    return {"id": document_id, "segments_created": len(pieces)}


@app.get("/api/v1/projects/{project_id}/segments")
def list_segments(project_id: str, user_id: str = Depends(current_user)):
    with db.connection() as con:
        rows = con.execute("SELECT id, chapter, ordinal, original_text, status, audio_path FROM text_segments WHERE project_id = ? AND tenant_id = ? ORDER BY chapter, ordinal", (project_id, user_id)).fetchall()
    return [{**dict(row), "playback_url": f"/api/v1/playback/{row['id']}" if row["audio_path"] else None} for row in rows]


def generate(job_id: str, segment_id: str, user_id: str, speaker: str) -> None:
    with db.connection() as con:
        con.execute("UPDATE generation_jobs SET status = 'running' WHERE id = ?", (job_id,))
        con.execute("UPDATE text_segments SET status = 'running' WHERE id = ? AND tenant_id = ?", (segment_id, user_id))
        segment = con.execute("SELECT normalized_text FROM text_segments WHERE id = ? AND tenant_id = ?", (segment_id, user_id)).fetchone()
    # The user may delete a queued title just before this worker begins it.
    # Treat that as a cancelled job without terminating the worker thread.
    if not segment:
        return
    try:
        target = settings.storage_dir / "segments" / user_id / f"{segment_id}.wav"
        if settings.tts_engine == "qwen":
            if speaker.startswith("profile:"):
                profile_id = speaker.removeprefix("profile:")
                with db.connection() as con:
                    profile = con.execute("SELECT audio_path, reference_text FROM voice_profiles WHERE id = ? AND tenant_id = ?", (profile_id, user_id)).fetchone()
                if not profile:
                    raise ValueError("Das gewählte eigene Stimmprofil existiert nicht mehr")
                from qwen_worker import synthesize_clone
                synthesize_clone(
                    segment["normalized_text"], target, model_id=settings.qwen_clone_model_id,
                    cache_dir=settings.root / "runtime" / "cache" / "huggingface",
                    reference_audio=Path(profile["audio_path"]), reference_text=profile["reference_text"], language=settings.qwen_language,
                )
            else:
                from qwen_worker import synthesize as qwen_synthesize

                qwen_synthesize(
                    segment["normalized_text"], target, model_id=settings.qwen_model_id,
                    cache_dir=settings.root / "runtime" / "cache" / "huggingface", speaker=speaker,
                    language=settings.qwen_language, instruct=settings.qwen_instruct,
                )
        elif settings.tts_engine == "mock":
            synthesize(segment["normalized_text"], target)
        else:
            raise ValueError(f"Unsupported TTS engine: {settings.tts_engine}")
        with db.connection() as con:
            still_exists = con.execute("SELECT id FROM text_segments WHERE id = ? AND tenant_id = ?", (segment_id, user_id)).fetchone()
            if still_exists:
                con.execute("UPDATE text_segments SET status = 'ready', audio_path = ? WHERE id = ? AND tenant_id = ?", (str(target), segment_id, user_id))
                con.execute("UPDATE generation_jobs SET status = 'completed', finished_at = ? WHERE id = ?", (now(), job_id))
            else:
                remove_owned_file(str(target))
    except Exception as exc:
        with db.connection() as con:
            con.execute("UPDATE text_segments SET status = 'failed' WHERE id = ? AND tenant_id = ?", (segment_id, user_id))
            con.execute("UPDATE generation_jobs SET status = 'failed', error = ?, finished_at = ? WHERE id = ?", (str(exc), now(), job_id))


def run_generation_worker() -> None:
    """Run one CPU-bound TTS job at a time, ordered by caller priority."""
    while True:
        _, _, job_id, segment_id, user_id, speaker = generation_queue.get()
        try:
            with db.connection() as con:
                job = con.execute("SELECT status FROM generation_jobs WHERE id = ?", (job_id,)).fetchone()
            if job and job["status"] == "queued":
                generate(job_id, segment_id, user_id, speaker)
        finally:
            generation_queue.task_done()


@app.post("/api/v1/generations", status_code=202)
async def request_generation(data: GenerationIn, user_id: str = Depends(current_user)):
    speaker = data.speaker or settings.qwen_speaker
    if not speaker.startswith("profile:") and speaker.lower() not in {item.lower() for item in SUPPORTED_SPEAKERS}:
        raise HTTPException(status_code=422, detail="Nicht unterstützte Qwen-Stimme")
    with db.connection() as con:
        segment = con.execute("SELECT id, status FROM text_segments WHERE id = ? AND tenant_id = ?", (data.segment_id, user_id)).fetchone()
        if not segment:
            raise HTTPException(status_code=404, detail="Segment nicht gefunden")
        if segment["status"] in {"queued", "running"}:
            return {"job_id": None, "status": segment["status"]}
        job_id = str(uuid.uuid4())
        con.execute("INSERT INTO generation_jobs (id, tenant_id, segment_id, status, priority, error, created_at, finished_at, speaker) VALUES (?, ?, ?, 'queued', ?, NULL, ?, NULL, ?)", (job_id, user_id, data.segment_id, data.priority, now(), speaker))
        con.execute("UPDATE text_segments SET status = 'queued' WHERE id = ?", (data.segment_id,))
    global generation_sequence
    with generation_sequence_lock:
        generation_sequence += 1
        sequence = generation_sequence
    # Higher API priority must be served first; the sequence preserves FIFO for ties.
    generation_queue.put((-data.priority, sequence, job_id, data.segment_id, user_id, speaker))
    return {"job_id": job_id, "status": "queued"}


@app.post("/api/v1/projects/{project_id}/generations", status_code=202)
def request_project_generation(project_id: str, data: ProjectGenerationIn, user_id: str = Depends(current_user)):
    """Queue every missing title, keeping interactive playback jobs ahead of this batch."""
    speaker = data.speaker or settings.qwen_speaker
    if not speaker.startswith("profile:") and speaker.lower() not in {item.lower() for item in SUPPORTED_SPEAKERS}:
        raise HTTPException(status_code=422, detail="Nicht unterstützte Qwen-Stimme")
    with db.connection() as con:
        project = con.execute("SELECT id FROM projects WHERE id = ? AND tenant_id = ?", (project_id, user_id)).fetchone()
        if not project:
            raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
        segments = con.execute("SELECT id FROM text_segments WHERE project_id = ? AND tenant_id = ? AND status NOT IN ('ready', 'queued', 'running') ORDER BY chapter, ordinal", (project_id, user_id)).fetchall()
        jobs = [(str(uuid.uuid4()), row["id"]) for row in segments]
        for job_id, segment_id in jobs:
            con.execute("INSERT INTO generation_jobs (id, tenant_id, segment_id, status, priority, error, created_at, finished_at, speaker) VALUES (?, ?, ?, 'queued', 10, NULL, ?, NULL, ?)", (job_id, user_id, segment_id, now(), speaker))
            con.execute("UPDATE text_segments SET status = 'queued' WHERE id = ? AND tenant_id = ?", (segment_id, user_id))
    global generation_sequence
    with generation_sequence_lock:
        for job_id, segment_id in jobs:
            generation_sequence += 1
            generation_queue.put((-10, generation_sequence, job_id, segment_id, user_id, speaker))
    return {"queued": len(jobs)}


@app.get("/api/v1/events")
async def events(user_id: str = Depends(current_user)):
    async def stream():
        for _ in range(30):
            with db.connection() as con:
                rows = con.execute("SELECT id, segment_id, status, error FROM generation_jobs WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 20", (user_id,)).fetchall()
            yield f"data: {json.dumps([dict(row) for row in rows])}\n\n"
            await asyncio.sleep(1)
    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/v1/playback/{segment_id}")
def playback(segment_id: str, user_id: str = Depends(current_user)):
    with db.connection() as con:
        row = con.execute("SELECT audio_path FROM text_segments WHERE id = ? AND tenant_id = ?", (segment_id, user_id)).fetchone()
    if not row or not row["audio_path"] or not Path(row["audio_path"]).is_file():
        raise HTTPException(status_code=404, detail="Audio noch nicht verfügbar")
    return FileResponse(row["audio_path"], media_type="audio/wav", filename=f"{segment_id}.wav")


@app.post("/api/v1/exports/{project_id}")
def export_project(project_id: str, user_id: str = Depends(current_user)):
    with db.connection() as con:
        rows = con.execute("SELECT ordinal, audio_path FROM text_segments WHERE project_id = ? AND tenant_id = ? AND audio_path IS NOT NULL ORDER BY ordinal", (project_id, user_id)).fetchall()
    if not rows:
        raise HTTPException(status_code=409, detail="Keine fertigen Audiodateien vorhanden")
    target = settings.storage_dir / "exports" / user_id / f"{project_id}.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for row in rows:
            archive.write(row["audio_path"], f"segment-{row['ordinal']:04d}.wav")
    return {"download_url": f"/api/v1/exports/{project_id}/download"}


@app.get("/api/v1/exports/{project_id}/download")
def download_export(project_id: str, user_id: str = Depends(current_user)):
    target = settings.storage_dir / "exports" / user_id / f"{project_id}.zip"
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Export nicht gefunden")
    return FileResponse(target, media_type="application/zip", filename="kr-cloud-voice-export.zip")
