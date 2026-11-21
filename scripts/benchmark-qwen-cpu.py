from __future__ import annotations

import json
import os
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "tts_worker"))
cache_dir = ROOT / "runtime" / "cache" / "huggingface"
os.environ["HF_HOME"] = str(cache_dir)
os.environ["TRANSFORMERS_CACHE"] = str(cache_dir)
os.environ["KRCV_SOX_DIR"] = str(ROOT / "runtime" / "sox" / "sox-14.4.2")
os.environ["PATH"] = f"{os.environ['KRCV_SOX_DIR']}{os.pathsep}{os.environ.get('PATH', '')}"

from qwen_worker import _load_model, synthesize  # noqa: E402

model_id = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
target = ROOT / "benchmarks" / "qwen-cpu-benchmark.wav"
started = time.perf_counter()
_load_model(model_id, cache_dir)
model_load_seconds = time.perf_counter() - started

text = "Dies ist eine repräsentative Messung der lokalen Qwen CPU Spracherzeugung für KR Cloud Voice."
started = time.perf_counter()
synthesize(text, target, model_id=model_id, cache_dir=cache_dir, speaker="Vivian", language="German")
generation_seconds = time.perf_counter() - started
with wave.open(str(target), "rb") as audio:
    audio_seconds = audio.getnframes() / audio.getframerate()

result = {
    "model_id": model_id,
    "model_load_seconds": round(model_load_seconds, 3),
    "generation_seconds": round(generation_seconds, 3),
    "audio_seconds": round(audio_seconds, 3),
    "realtime_factor": round(generation_seconds / audio_seconds, 3),
    "wav": str(target),
}
(ROOT / "benchmarks" / "qwen-cpu-benchmark.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result))
