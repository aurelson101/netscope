#!/bin/sh
set -eu

# Bind-mounted log directories are often created as root by Docker. Prepare
# the mount before dropping privileges so every backend service can log there.
if [ -n "${LOG_FILE:-}" ]; then
    log_directory=$(dirname "$LOG_FILE")
    mkdir -p "$log_directory"
    chown -R netscope:netscope "$log_directory"
fi

exec gosu netscope "$@"
