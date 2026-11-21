$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$env:KRCV_ROOT = $root
$env:KRCV_STORAGE_DIR = "$root\storage"
$env:HF_HOME = "$root\runtime\cache\huggingface"
$env:TRANSFORMERS_CACHE = $env:HF_HOME
$env:KRCV_SOX_DIR = "$root\runtime\sox\sox-14.4.2"
$env:PATH = "$env:KRCV_SOX_DIR;$env:PATH"
$env:KRCV_TTS_ENGINE = if ($env:KRCV_TTS_ENGINE) { $env:KRCV_TTS_ENGINE } else { 'qwen' }
$env:PIP_CACHE_DIR = "$root\runtime\cache\pip"
$env:TEMP = "$root\runtime\temp"; $env:TMP = $env:TEMP
$env:PYTHONNOUSERSITE = '1'
$python = "$root\runtime\python\python.exe"
if (-not (Test-Path $python)) { throw 'Portable Python-Laufzeit fehlt unter runtime\python.' }
# Qwen writes model/cache metadata below runtime while loading. Do not use
# Uvicorn's source watcher here: it would restart and abort active TTS jobs.
& $python -s -m uvicorn app.main:app --app-dir "$root\apps\api" --host 127.0.0.1 --port 8000
