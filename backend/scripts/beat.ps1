# Levanta Celery Beat (el programador de horarios). Va en una terminal aparte del worker.
#   .\scripts\beat.ps1
if (-not $env:VIRTUAL_ENV) {
    Write-Error "Activa primero el entorno virtual (venv\Scripts\Activate.ps1)."
    exit 1
}
Set-Location (Join-Path $PSScriptRoot "..")
celery -A config beat --loglevel=info