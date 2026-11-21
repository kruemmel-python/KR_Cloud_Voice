# KR Cloud Voice

Lokale, später cloudfähige Multi-Tenant-TTS-Plattform. Die V1 liefert einen
vollständig verwendbaren Entwicklungsweg mit FastAPI, React, mandantensicherem
SQLite-Entwicklungsspeicher und Qwen3-TTS-CPU-Inferenz. Ein deterministischer
WAV-Mock steht zusätzlich für schnelle Integrationstests bereit.

## Schnellstart

1. Die enthaltenen portablen Runtimes unter `runtime\python`, `runtime\node`
   und `runtime\sox` verwenden. Es wird absichtlich kein System-Python benötigt.
2. `scripts/bootstrap.ps1` ausführen.
3. In zwei PowerShell-Fenstern `scripts/start-api.ps1` und
   `scripts/start-web.ps1` ausführen.
4. `http://127.0.0.1:5173` öffnen.

Alle bewusst gesetzten Cache-, Modell- und temporären Pfade zeigen auf `H:`.
Für den Entwicklungsmodus ist SQLite absichtlich die Standardimplementierung.
Die PostgreSQL-, Redis- und S3-Adapter bleiben über die Konfiguration
umschaltbar; sie werden erst aktiviert, wenn die jeweiligen lokalen Dienste
kontrolliert auf `H:` installiert sind.

## Funktionen der V1

- Registrierung und Anmeldung mit Argon2-Hashing und signierten JWTs
- Mandantengetrennte Projekte und Dokumente
- TXT/MD-Upload, Kapitel- und Segmentierung sowie Einzelneugenerierung
- Warteschlange mit Playback-Priorität und SSE-Statusstrom
- Echte lokale CPU-Spracherzeugung mit `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice`
- Sofort spielbare, valide WAV-Dateien über Qwen oder den Mock-Worker
- Download von WAV und ZIP-Export je Projekt
- React-Oberfläche für Anmeldung, Upload, Generierung und Wiedergabe

## Qwen-CPU-Modus

`scripts/start-api.ps1` aktiviert standardmäßig Qwen. Beim ersten Erzeugen
lädt die Anwendung die Modellgewichte in `runtime\cache\huggingface`; danach
arbeitet sie lokal. Für schnelle Tests ist `KRCV_TTS_ENGINE=mock` verfügbar.
Die erste erfolgreich geprüfte echte Testdatei liegt unter
`benchmarks\qwen-first-test-generation.wav`.

PostgreSQL, Redis, MinIO und FFmpeg bleiben optionale Erweiterungen für den
späteren Produktionsbetrieb; die aktuelle V1 ist lokal mit SQLite lauffähig.
