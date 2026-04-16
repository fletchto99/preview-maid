#!/bin/sh
set -e

# Fix ownership of mounted volumes so appuser can write to them
if [ -d /app/logs ]; then
    chown appuser:appuser /app/logs
fi

exec gosu appuser "$@"
