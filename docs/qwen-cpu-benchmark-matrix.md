# Kontrollierter Qwen-CPU-Matrixlauf

## Ziel

Der Lauf misst den Einfluss der PyTorch-Intra-Op-Threadzahl auf die echte
Qwen3-TTS-CPU-Inferenz. Er variiert nur die Threadzahl und die feste
Textlänge; Modell, Stimme, Sprache, Sampling, Modellcache und Interop-Threads
bleiben konstant.

## Matrix

| Variable | Werte |
| --- | --- |
| PyTorch-Intra-Op-Threads | 3, 6, 12 |
| PyTorch-Interop-Threads | 1 |
| Texte | kurz, mittel, lang |
| Wiederholungen | 1 pro Zelle |
| Modell | Qwen3-TTS-12Hz-0.6B-CustomVoice |
| Stimme / Sprache | Vivian / German |

Die Messung erfolgt mit bereits geladenem Modell. Die separate Kaltstartzeit
wird zusätzlich protokolliert und nicht in den RTF eingerechnet.

## Ergebnisdateien

- Rohdaten: `benchmarks/qwen-cpu-matrix.jsonl`
- WAVs jeder Matrixzelle: `benchmarks/matrix-wav/`
- Skript: `scripts/benchmark-qwen-matrix.py`

Der RTF ist `Generierungszeit / Audiolänge`. Kleinere Werte sind besser.
