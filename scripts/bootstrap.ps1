$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root 'runtime\python\python.exe'
if (-not (Test-Path $python)) { $python = Join-Path $root 'runtime\python\bin\python.exe' }
if (-not (Test-Path $python)) { throw 'Portable Python 3.12 x64 fehlt unter runtime\python. Kein System-Python wird verwendet.' }
$env:HF_HOME = "$root\runtime\cache\huggingface"
$env:TRANSFORMERS_CACHE = $env:HF_HOME
$env:HF_HUB_CACHE = "$env:HF_HOME\hub"
$env:HF_ASSETS_CACHE = "$env:HF_HOME\assets"
$env:TORCH_HOME = "$root\runtime\cache\torch"
$env:PIP_CACHE_DIR = "$root\runtime\cache\pip"
$env:npm_config_cache = "$root\runtime\cache\npm"
$env:TEMP = "$root\runtime\temp"
$env:TMP = $env:TEMP
$env:PYTHONNOUSERSITE = '1'
$env:PIP_CONFIG_FILE = "$root\runtime\pip-pypi-only.ini"
@($env:HF_HOME,$env:HF_HUB_CACHE,$env:HF_ASSETS_CACHE,$env:TORCH_HOME,$env:PIP_CACHE_DIR,$env:npm_config_cache,$env:TEMP,"$root\runtime\logs") | ForEach-Object { New-Item -ItemType Directory -Force $_ | Out-Null }
if ((& $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')") -ne '3.12') { throw 'KR Cloud Voice V1 verlangt Python 3.12.' }
# Die Embeddable-Distribution wird absichtlich direkt als isolierte
# Projektlaufzeit verwendet; ihre Site-Packages bleiben unter runtime\python.
& $python -s -m pip install --upgrade pip
& $python -s -m pip install -r "$root\requirements.txt"
Push-Location "$root\apps\web"
$node = Join-Path $root 'runtime\node\node.exe'
$npm = Join-Path $root 'runtime\node\npm.cmd'
if (-not (Test-Path $node) -or -not (Test-Path $npm)) { throw 'Portable Node.js LTS fehlt unter runtime\node. Kein System-Node wird verwendet.' }
& $npm install
Pop-Location
Write-Host 'Bootstrap abgeschlossen. Alle Projekt-Caches und die Qwen-CPU-Runtime zeigen auf H:.'
