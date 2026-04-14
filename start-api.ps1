# Run from repo root (recommended). Starts FastAPI from `medical_chatbot/`.
$appDir = Join-Path $PSScriptRoot 'medical_chatbot'
$mainPy = Join-Path $appDir 'src\main.py'

if (-not (Test-Path $mainPy)) {
    Write-Error 'Expected medical_chatbot\src\main.py. Run this script from the Medical-Chatbot repo root.'
    exit 1
}

Set-Location $appDir

$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (Test-Path $venvPython) {
    & $venvPython -m uvicorn src.main:app --reload
    exit $LASTEXITCODE
}

python -m uvicorn src.main:app --reload
