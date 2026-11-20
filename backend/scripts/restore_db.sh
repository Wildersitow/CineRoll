#!/usr/bin/env bash
# Restaura un respaldo en una base NUEVA (cineroll_restauracion) para comprobarlo,
# sin tocar la base real:
#   ./scripts/restore_db.sh ~/respaldos-cineroll/cineroll_20261201_030000.sql.gz
set -euo pipefail

if [ $# -ne 1 ] || [ ! -f "$1" ]; then
  echo "Uso: $0 <archivo.sql.gz>" >&2
  exit 1
fi

cd "$(dirname "$0")/.."
COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.prod"
set -a
# shellcheck disable=SC1091
source .env.prod
set +a

PRUEBA="cineroll_restauracion"

$COMPOSE exec -T db psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $PRUEBA;"
$COMPOSE exec -T db psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $PRUEBA;"
gunzip -c "$1" | $COMPOSE exec -T db psql -U "$DB_USER" -d "$PRUEBA" -v ON_ERROR_STOP=1 -q

echo "Restaurado en la base '$PRUEBA'. Comprobación rápida:"
$COMPOSE exec -T db psql -U "$DB_USER" -d "$PRUEBA" -c \
  "SELECT 'media' AS tabla, count(*) FROM media_media
   UNION ALL SELECT 'funciones', count(*) FROM cines_funcion
   UNION ALL SELECT 'usuarios', count(*) FROM usuarios_usuario;"