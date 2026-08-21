# PowerShell equivalent of `make setup`, for teammates without GNU make.
# Usage: .\scripts\setup.ps1

python -m venv .venv
$venvPython = ".venv\Scripts\python.exe"

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -e trust
& $venvPython -m pip install pytest pytest-cov hypothesis ruff
# statsmodels deliberately skipped - see docs/RISKS.md R7 (pulls in
# numpy/scipy/pandas for one optional cross-validation test that skips
# gracefully without it). Install it yourself if you need that one test:
# pip install statsmodels

if ((Test-Path backend\pyproject.toml) -or (Test-Path backend\requirements.txt)) {
    & $venvPython -m pip install -e backend
} else {
    Write-Host "backend/ has no pyproject.toml or requirements.txt yet - skipping (see docs/DEADLINES.md)"
}

if ((Test-Path governance\pyproject.toml) -or (Test-Path governance\requirements.txt)) {
    & $venvPython -m pip install -e governance
} else {
    Write-Host "governance/ has no pyproject.toml or requirements.txt yet - skipping (see docs/DEADLINES.md)"
}

Write-Host "Done. Next: .\scripts\up.ps1"
