#!/usr/bin/env bash
# Respaldo diario de PostgreSQL. Se ejecuta en el SERVIDOR, desde cron.
#   ./scripts/backup_db.sh
# Deja un archivo comprimido en $BACKUP_DIR (por defecto ~/respaldos-cineroll)
# y borra los que tengan más de $RETENCION_DIAS días (por defecto 14).
set -euo pipefail

# Carpeta del backend (donde están docker-compose.prod.yml y .env.prod)
cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-$HOME/respaldos-cineroll}"
RETENCION_DIAS="${RETENCION_DIAS:-14}"
COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.prod"

# Lee DB_USER y DB_NAME del mismo .env.prod que usa Django (una sola fuente de verdad).
set -a
# shellcheck disable=SC1091
source .env.prod
set +a

mkdir -p "$BACKUP_DIR"
ARCHIVO="$BACKUP_DIR/cineroll_$(date +%Y%m%d_%H%M%S).sql.gz"

# -T: sin terminal (necesario bajo cron). --no-owner/--no-acl: el respaldo se puede
# restaurar con otro usuario sin errores de permisos.
$COMPOSE exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl \
  | gzip > "$ARCHIVO.tmp"

# Solo se conserva si pg_dump terminó bien y el archivo no está vacío.
if [ ! -s "$ARCHIVO.tmp" ]; then
  rm -f "$ARCHIVO.tmp"
  echo "ERROR: el respaldo salió vacío" >&2
  exit 1
fi
mv "$ARCHIVO.tmp" "$ARCHIVO"

# Borra respaldos antiguos
find "$BACKUP_DIR" -name 'cineroll_*.sql.gz' -mtime +"$RETENCION_DIAS" -delete

echo "$(date '+%Y-%m-%d %H:%M:%S') respaldo creado: $ARCHIVO ($(du -h "$ARCHIVO" | cut -f1))"