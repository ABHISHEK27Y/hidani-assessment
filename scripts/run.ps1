param(
    [ValidateRange(1024, 65535)][int]$Port = 8000,
    [switch]$SkipInstall
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.11 or newer, then rerun this script.' }
    }
    $projectPython = Join-Path $projectRoot '.venv/Scripts/python.exe'
    if (-not $SkipInstall) {
        & $projectPython -m pip install -r requirements.txt -c constraints.txt
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check your network and rerun.' }
    }
    if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
    Write-Host "Orbit: http://127.0.0.1:$Port  |  API docs: http://127.0.0.1:$Port/docs"
    & $projectPython -m uvicorn app.main:app --host 127.0.0.1 --port $Port --no-access-log
    if ($LASTEXITCODE -ne 0) { throw 'Server exited with an error. Check whether the selected port is already in use.' }
} finally { Pop-Location }
