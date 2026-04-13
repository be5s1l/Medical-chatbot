# Run from repo root OR from medical_chatbot — starts FastAPI with correct cwd and .env
$appDir = Join-Path $PSScriptRoot "medical_chatbot"
if (-not (Test-Path (Join-Path $appDir "src\main.py"))) {
    Write-Error "Expected medical_chatbot\src\main.py — run this script from the Medical-Chatbot repo root."
    exit 1
}
Set-Location $appDir
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    & $venvPython -m uvicorn src.main:app --reload
} else {
    python -m uvicorn src.main:app --reload
}
