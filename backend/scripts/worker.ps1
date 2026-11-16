# Levanta el worker de Celery en Windows. Ejecutar desde cualquier carpeta con el venv activo:
#   .\scripts\worker.ps1
# --pool=solo es obligatorio en Windows: el pool por defecto (prefork) no funciona allí.
# Contrapartida: con "solo" los límites de tiempo de las tareas NO se aplican.
if (-not $env:VIRTUAL_ENV) {
    Write-Error "Activa primero el entorno virtual (venv\Scripts\Activate.ps1)."
    exit 1
}
Set-Location (Join-Path $PSScriptRoot "..")
celery -A config worker --pool=solo --loglevel=info