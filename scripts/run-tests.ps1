$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = "$root\runtime\python\python.exe"
if (-not (Test-Path $python)) { throw 'Portable Python-Laufzeit fehlt unter runtime\python.' }
& $python -m unittest discover -s "$root\tests\unit" -v
