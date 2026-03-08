param (
    [string]$Command = ""
)

$Python = "venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

switch ($Command) {
    "streamlit" {
        Write-Host "Starting Streamlit..." -ForegroundColor Cyan
        & $Python -m streamlit run src/app.py
    }
    "test" {
        Write-Host "Running tests..." -ForegroundColor Cyan
        & $Python -m pytest
    }
    Default {
        Write-Host "Starting Main..." -ForegroundColor Cyan
        & $Python -m src.main
    }
}
