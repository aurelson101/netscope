#!/bin/sh
set -eu

compose_file=${COMPOSE_FILE:-docker-compose.yml}
log_since=${LOG_SINCE:-10m}
base_url=${NETSCOPE_URL:-http://localhost:${HTTP_PORT:-8080}}
failed=0

compose() {
    docker compose -f "$compose_file" "$@"
}

echo "== Configuration Docker =="
compose config --quiet

echo "== État des services =="
compose ps
for service in $(compose config --services); do
    container_id=$(compose ps -q "$service")
    if [ -z "$container_id" ]; then
        echo "ERREUR: $service n'a pas de conteneur actif"
        failed=1
        continue
    fi
    state=$(docker inspect -f '{{.State.Status}}' "$container_id")
    health=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id")
    if [ "$state" != "running" ] || [ "$health" = "unhealthy" ]; then
        echo "ERREUR: $service state=$state health=$health"
        failed=1
    fi
done

echo "== Vérification HTTP =="
if ! curl -fsS --max-time 10 "$base_url/health" >/dev/null; then
    echo "ERREUR: $base_url/health ne répond pas"
    failed=1
else
    echo "OK: $base_url/health"
fi

echo "== Espace disque et journaux =="
available_percent=$(df -Pk . | awk 'NR==2 {gsub("%", "", $5); print 100-$5}')
if [ "$available_percent" -lt 10 ]; then
    echo "ERREUR: moins de 10 % d'espace disque disponible"
    failed=1
else
    echo "OK: ${available_percent}% d'espace disque disponible"
fi
large_logs=$(find logs -type f -size +100M -print 2>/dev/null || true)
if [ -n "$large_logs" ]; then
    echo "ERREUR: journaux de plus de 100 Mio détectés"
    echo "$large_logs"
    failed=1
else
    echo "OK: aucun journal supérieur à 100 Mio"
fi

echo "== Erreurs récentes ($log_since) =="
log_file=$(mktemp)
trap 'rm -f "$log_file"' EXIT HUP INT TERM
compose logs --no-color --since "$log_since" >"$log_file" 2>&1 || true
if grep -Eai 'permission denied|traceback|fatal|panic|unhandled_request_error|connection refused|no space left|out of memory|killed process' "$log_file"; then
    echo "ERREUR: anomalies détectées dans les journaux récents"
    failed=1
else
    echo "OK: aucune anomalie connue détectée"
fi

if [ "$failed" -ne 0 ]; then
    echo "Diagnostic NetScope: ÉCHEC"
    exit 1
fi
echo "Diagnostic NetScope: OK"
