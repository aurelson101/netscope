#!/usr/bin/env python3
import http.client
import json
import os
import shutil
import socket
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote

SOCKET_PATH = os.getenv("DOCKER_SOCKET", "/var/run/docker.sock")
PROJECT = os.getenv("COMPOSE_PROJECT_NAME", "netscope")
DISK_PATH = os.getenv("DISK_PATH", "/host/logs")
EXPECTED_SERVICES = {
    item.strip()
    for item in os.getenv(
        "EXPECTED_SERVICES",
        "postgres,redis,backup,backend-api,docker-monitor,worker,scheduler,scanner,frontend",
    ).split(",")
    if item.strip()
}


class UnixConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(SOCKET_PATH)


def docker_get(path: str):
    connection = UnixConnection("localhost", timeout=5)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        payload = response.read()
        if response.status >= 400:
            raise RuntimeError(f"Docker API HTTP {response.status}")
        return json.loads(payload)
    finally:
        connection.close()


def snapshot() -> dict:
    summaries = docker_get("/containers/json?all=1")
    containers = []
    for summary in summaries:
        labels = summary.get("Labels") or {}
        if labels.get("com.docker.compose.project") != PROJECT:
            continue
        details = docker_get(f"/containers/{quote(summary['Id'])}/json")
        state = details.get("State") or {}
        health = (state.get("Health") or {}).get("Status", "none")
        service = labels.get("com.docker.compose.service", "unknown")
        healthy = state.get("Status") == "running" and health not in ("unhealthy", "starting")
        containers.append({
            "service": service,
            "name": (summary.get("Names") or [service])[0].lstrip("/"),
            "state": state.get("Status", "unknown"),
            "health": health,
            "healthy": healthy,
            "restarts": details.get("RestartCount", 0),
            "started_at": state.get("StartedAt"),
        })
    present = {item["service"] for item in containers}
    for service in EXPECTED_SERVICES - present:
        containers.append({
            "service": service,
            "name": service,
            "state": "missing",
            "health": "none",
            "healthy": False,
            "restarts": 0,
            "started_at": None,
        })
    containers.sort(key=lambda item: item["service"])
    total, used, free = shutil.disk_usage(DISK_PATH)
    disk = {
        "total_bytes": total,
        "used_bytes": used,
        "free_bytes": free,
        "used_percent": round(used * 100 / total, 1) if total else 0,
        "free_percent": round(free * 100 / total, 1) if total else 0,
    }
    return {
        "status": "healthy" if containers and all(item["healthy"] for item in containers) else "critical",
        "containers": containers,
        "disk": disk,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/health", "/snapshot"):
            self.send_error(404)
            return
        try:
            payload = snapshot()
            status = 200
        except Exception as exc:
            payload = {"status": "critical", "error": str(exc)[:200], "containers": []}
            status = 503
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8090), Handler).serve_forever()
