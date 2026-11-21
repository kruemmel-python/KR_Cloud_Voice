from __future__ import annotations

"""Controlled warm-model CPU benchmark matrix for Qwen3-TTS.

The same model, voice, language, sampling settings and inter-op threading are
used in every row. Only the PyTorch intra-op thread count and text length vary.
Results are appended after each completed row so an interrupted run is usable.
"""

import argparse
import json
import os
import platform
import sys
import time
import wave
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "tts_worker"))
CACHE = ROOT / "runtime" / "cache" / "huggingface"
OUT = ROOT / "benchmarks" / "qwen-cpu-matrix.jsonl"
WAV_DIR = ROOT / "benchmarks" / "matrix-wav"
os.environ["HF_HOME"] = str(CACHE)
os.environ["TRANSFORMERS_CACHE"] = str(CACHE)
os.environ["KRCV_SOX_DIR"] = str(ROOT / "runtime" / "sox" / "sox-14.4.2")
os.environ["PATH"] = f"{os.environ['KRCV_SOX_DIR']}{os.pathsep}{os.environ.get('PATH', '')}"

import torch  # noqa: E402

torch.set_num_interop_threads(1)
from qwen_worker import _load_model, synthesize  # noqa: E402

MODEL = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
TEXTS = {
    "short": "Am Morgen begann die Reise.",
    "medium": "Am Morgen begann die Reise. Der Zug glitt durch den Nebel, während Mira am Fenster saß und auf die dunklen Wälder hinausblickte.",
    "long": "Am Morgen begann die Reise. Der Zug glitt durch den Nebel, während Mira am Fenster saß und auf die dunklen Wälder hinausblickte. In ihrer Tasche lag ein Brief, den sie seit Tagen nicht geöffnet hatte. Erst als die ersten Häuser der Küstenstadt auftauchten, fasste sie Mut und las die wenigen Zeilen.",
}


def duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, nargs="+", default=[3, 6, 12])
    parser.add_argument("--repeats", type=int, default=1)
    args = parser.parse_args()
    WAV_DIR.mkdir(parents=True, exist_ok=True)

    loaded = time.perf_counter()
    _load_model(MODEL, CACHE)
    model_load_seconds = time.perf_counter() - loaded
    print(json.dumps({"event": "model_loaded", "seconds": round(model_load_seconds, 3)}), flush=True)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with OUT.open("a", encoding="utf-8") as report:
        for threads in args.threads:
            torch.set_num_threads(threads)
            for label, text in TEXTS.items():
                for repeat in range(1, args.repeats + 1):
                    wav = WAV_DIR / f"{run_id}-t{threads}-{label}-r{repeat}.wav"
                    started = time.perf_counter()
                    synthesize(text, wav, model_id=MODEL, cache_dir=CACHE, speaker="Vivian", language="German")
                    generation_seconds = time.perf_counter() - started
                    audio_seconds = duration(wav)
                    row = {
                        "run_id": run_id,
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "hardware": platform.processor(),
                        "logical_cpus": os.cpu_count(),
                        "model_id": MODEL,
                        "model_load_seconds": round(model_load_seconds, 3),
                        "torch_threads": threads,
                        "torch_interop_threads": 1,
                        "text_length": label,
                        "text_characters": len(text),
                        "repeat": repeat,
                        "generation_seconds": round(generation_seconds, 3),
                        "audio_seconds": round(audio_seconds, 3),
                        "realtime_factor": round(generation_seconds / audio_seconds, 3),
                        "wav": str(wav),
                    }
                    report.write(json.dumps(row, ensure_ascii=False) + "\n")
                    report.flush()
                    print(json.dumps(row, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
