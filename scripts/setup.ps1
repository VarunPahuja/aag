# PowerShell equivalent of `make setup`, for teammates without GNU make.
# Usage: .\scripts\setup.ps1

python -m venv .venv
$venvPython = ".venv\Scripts\python.exe"

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -e trust -e simulator -e governance -e backend
& $venvPython -m pip install pytest pytest-cov pytest-asyncio hypothesis httpx ruff
# statsmodels deliberately skipped - see docs/RISKS.md R7 (pulls in
# numpy/scipy/pandas for one optional cross-validation test that skips
# gracefully without it). Install it yourself if you need that one test:
# pip install statsmodels

Write-Host "Done. Next: .\scripts\up.ps1"
