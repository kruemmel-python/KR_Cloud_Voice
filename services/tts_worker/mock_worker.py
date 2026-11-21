from __future__ import annotations

import math
import wave
from pathlib import Path


def synthesize(text: str, destination: Path, sample_rate: int = 22050) -> None:
    """Create a short valid mono WAV; used only for platform integration tests."""
    seconds = max(0.25, min(4.0, len(text) / 45))
    frames = int(seconds * sample_rate)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        samples = bytearray()
        for i in range(frames):
            envelope = min(1, i / 500) * min(1, (frames - i) / 500)
            value = int(4500 * envelope * math.sin(2 * math.pi * 220 * i / sample_rate))
            samples.extend(value.to_bytes(2, "little", signed=True))
        audio.writeframes(samples)
