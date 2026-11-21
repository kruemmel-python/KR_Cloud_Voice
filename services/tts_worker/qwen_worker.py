from __future__ import annotations

"""CPU implementation for the Qwen3 CustomVoice model.

The model is deliberately loaded lazily: starting the API stays fast and the
large Hugging Face download is only triggered by the first real generation.
"""

import os
import threading
import gc
from pathlib import Path

_model = None
_model_id = None
_model_lock = threading.Lock()
_clone_prompts: dict[tuple[str, str], object] = {}


def _load_model(model_id: str, cache_dir: Path):
    global _model, _model_id, _clone_prompts
    with _model_lock:
        if _model is None or _model_id != model_id:
            # Keep only one Qwen model resident. On this CPU workstation two
            # 0.6B models at once can exhaust RAM.
            _model = None
            _model_id = None
            _clone_prompts = {}
            gc.collect()
            # Ignore a workstation-global cache path (for example a removed G:
            # drive). All model state must remain inside this project runtime.
            os.environ["HF_HOME"] = str(cache_dir)
            os.environ["TRANSFORMERS_CACHE"] = str(cache_dir)
            import torch
            from qwen_tts import Qwen3TTSModel

            cache_dir.mkdir(parents=True, exist_ok=True)
            _model = Qwen3TTSModel.from_pretrained(
                model_id,
                device_map="cpu",
                dtype=torch.float32,
                cache_dir=str(cache_dir),
            )
            _model_id = model_id
    return _model


def synthesize(
    text: str,
    destination: Path,
    *,
    model_id: str,
    cache_dir: Path,
    speaker: str,
    language: str,
    instruct: str | None = None,
) -> None:
    """Generate one WAV using Qwen3-TTS on CPU."""
    if not text.strip():
        raise ValueError("Text for Qwen generation must not be empty")

    # pysox locates its companion executable through PATH on Windows.
    sox_dir = os.getenv("KRCV_SOX_DIR")
    if sox_dir:
        os.environ["PATH"] = f"{sox_dir}{os.pathsep}{os.environ.get('PATH', '')}"

    model = _load_model(model_id, cache_dir)
    wavs, sample_rate = model.generate_custom_voice(
        text=text,
        speaker=speaker,
        language=language,
        instruct=instruct or None,
        do_sample=False,
        max_new_tokens=2048,
    )
    if not wavs:
        raise RuntimeError("Qwen returned no audio")

    import soundfile as sf

    destination.parent.mkdir(parents=True, exist_ok=True)
    sf.write(destination, wavs[0], sample_rate, subtype="PCM_16")


def synthesize_clone(
    text: str,
    destination: Path,
    *,
    model_id: str,
    cache_dir: Path,
    reference_audio: Path,
    reference_text: str,
    language: str,
) -> None:
    """Generate using Qwen's Base voice-cloning model and an approved WAV clip."""
    if not text.strip() or not reference_text.strip():
        raise ValueError("Text and reference transcript are required for voice cloning")
    model = _load_model(model_id, cache_dir)
    # Building the prompt encodes the complete reference recording. Reusing it
    # is essential on CPU: every later segment then needs only the target-text
    # synthesis rather than another pass over the user's voice recording.
    cache_key = (str(reference_audio.resolve()), reference_text)
    with _model_lock:
        prompt = _clone_prompts.get(cache_key)
        if prompt is None:
            prompt = model.create_voice_clone_prompt(
                ref_audio=str(reference_audio),
                ref_text=reference_text,
                x_vector_only_mode=False,
            )
            _clone_prompts[cache_key] = prompt
    wavs, sample_rate = model.generate_voice_clone(
        text=text,
        language=language,
        voice_clone_prompt=prompt,
        do_sample=False,
        max_new_tokens=2048,
    )
    if not wavs:
        raise RuntimeError("Qwen returned no audio")
    import soundfile as sf
    destination.parent.mkdir(parents=True, exist_ok=True)
    sf.write(destination, wavs[0], sample_rate, subtype="PCM_16")
