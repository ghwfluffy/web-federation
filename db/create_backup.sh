#!/bin/sh
set -eu

source_name="${1:-manual}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
suffix="$(tr -dc 'a-z0-9' </dev/urandom | head -c 6)"
filename="${timestamp}_${source_name}_${suffix}.dump"
manifest="${timestamp}_${source_name}_${suffix}.json"
backup_dir="${BACKUP_DIR:-/backups}"

mkdir -p "$backup_dir"

PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}" pg_dump \
  --host "${POSTGRES_HOST:?POSTGRES_HOST is required}" \
  --port "${POSTGRES_PORT:-5432}" \
  --username "${POSTGRES_USER:?POSTGRES_USER is required}" \
  --dbname "${POSTGRES_DB:?POSTGRES_DB is required}" \
  --format custom \
  --file "${backup_dir}/${filename}"

size_bytes="$(wc -c <"${backup_dir}/${filename}" | tr -d ' ')"
sha256="$(sha256sum "${backup_dir}/${filename}" | awk '{print $1}')"

cat >"${backup_dir}/${manifest}" <<EOF
{
  "filename": "${filename}",
  "source": "${source_name}",
  "created_at": "${timestamp}",
  "size_bytes": ${size_bytes},
  "sha256": "${sha256}"
}
EOF

if [ -n "${BACKUP_UID:-}" ] && [ -n "${BACKUP_GID:-}" ]; then
  chown "${BACKUP_UID}:${BACKUP_GID}" "${backup_dir}/${filename}" "${backup_dir}/${manifest}" || true
fi

printf '%s\n' "${backup_dir}/${filename}"
