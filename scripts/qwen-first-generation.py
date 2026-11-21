from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "tts_worker"))

os.environ["HF_HOME"] = str(ROOT / "runtime" / "cache" / "huggingface")
os.environ["TRANSFORMERS_CACHE"] = os.environ["HF_HOME"]
os.environ.setdefault("KRCV_SOX_DIR", str(ROOT / "runtime" / "sox" / "sox-14.4.2"))
os.environ["PATH"] = f"{os.environ['KRCV_SOX_DIR']}{os.pathsep}{os.environ.get('PATH', '')}"

from qwen_worker import synthesize  # noqa: E402

destination = ROOT / "benchmarks" / "qwen-first-test-generation.wav"
synthesize(
    "Dies ist die erste echte lokale Qwen-Testgenerierung für KR Cloud Voice.",
    destination,
    model_id="Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    cache_dir=ROOT / "runtime" / "cache" / "huggingface",
    speaker="Vivian",
    language="German",
)
print(destination)
