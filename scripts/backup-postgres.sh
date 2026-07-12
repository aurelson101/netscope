#!/bin/sh
set -eu

interval_hours="${BACKUP_INTERVAL_HOURS:-24}"
retention_days="${BACKUP_RETENTION_DAYS:-14}"

case "$interval_hours:$retention_days" in
  *[!0-9:]*|0:*|*:0) echo "BACKUP_INTERVAL_HOURS and BACKUP_RETENTION_DAYS must be positive integers" >&2; exit 2 ;;
esac

mkdir -p /backups /metrics

while true; do
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  destination="/backups/netscope-${timestamp}.dump"
  temporary="${destination}.tmp"

  if pg_dump --format=custom --no-owner --no-acl --file="$temporary"; then
    mv "$temporary" "$destination"
    chmod 600 "$destination"
    epoch="$(date +%s)"
    size="$(wc -c < "$destination" | tr -d ' ')"
    {
      echo '# HELP netscope_backup_last_success_timestamp_seconds Unix timestamp of the latest successful PostgreSQL backup.'
      echo '# TYPE netscope_backup_last_success_timestamp_seconds gauge'
      echo "netscope_backup_last_success_timestamp_seconds ${epoch}"
      echo '# HELP netscope_backup_last_size_bytes Size of the latest PostgreSQL backup.'
      echo '# TYPE netscope_backup_last_size_bytes gauge'
      echo "netscope_backup_last_size_bytes ${size}"
    } > /metrics/netscope-backup.prom.tmp
    mv /metrics/netscope-backup.prom.tmp /metrics/netscope-backup.prom
    find /backups -name 'netscope-*.dump' -type f -mtime "+${retention_days}" -delete
    echo "Backup completed: ${destination}"
  else
    rm -f "$temporary"
    echo "PostgreSQL backup failed" >&2
  fi

  sleep "$((interval_hours * 3600))"
done
