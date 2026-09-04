$ErrorActionPreference = "Stop"

$backendRoot = Split-Path -Parent $PSScriptRoot
$preferredPython = Join-Path $backendRoot ".venv\Scripts\python.exe"
$legacyPython = Join-Path $backendRoot "venv\Scripts\python.exe"

if (Test-Path -LiteralPath $preferredPython) {
    $python = $preferredPython
} elseif (Test-Path -LiteralPath $legacyPython) {
    Write-Warning "Using legacy backend/venv; recreate it as backend/.venv on the pinned Python version."
    $python = $legacyPython
} else {
    throw "Backend virtual environment not found. Create backend/.venv first."
}

Push-Location $backendRoot
try {
    & $python -m ruff check .
    if ($LASTEXITCODE -ne 0) { throw "Ruff failed." }

    & $python -m mypy main.py api core domain schemas scripts tests
    if ($LASTEXITCODE -ne 0) { throw "mypy failed." }

    & $python -m pytest
    if ($LASTEXITCODE -ne 0) { throw "pytest failed." }

    & $python -m scripts.export_openapi
    if ($LASTEXITCODE -ne 0) { throw "OpenAPI export failed." }
} finally {
    Pop-Location
}
