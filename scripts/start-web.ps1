$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$env:npm_config_cache = "$root\runtime\cache\npm"
$env:TEMP = "$root\runtime\temp"; $env:TMP = $env:TEMP
Push-Location "$root\apps\web"
$npm = Join-Path $root 'runtime\node\npm.cmd'
if (-not (Test-Path $npm)) { throw 'Portable Node.js LTS fehlt unter runtime\node.' }
& $npm run dev
