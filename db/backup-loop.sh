#!/bin/sh
set -eu

interval_minutes="${BACKUP_INTERVAL_MINUTES:-360}"

while true; do
  /opt/backup/create_backup.sh automatic || true
  sleep "$((interval_minutes * 60))"
done
