"""
param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    throw ".venv가 없습니다. 먼저 fix-pc-auto-builder.ps1을 실행하세요."
}

Set-Location (Join-Path $ProjectRoot "backend")
& $VenvPython -m uvicorn app.main:app --reload --host 127.0.0.1 --port $Port
"""