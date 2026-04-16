#!/bin/sh
set -e

# Fix ownership of mounted volumes so appuser can write to them
if [ -d /app/logs ]; then
    chown -R appuser:appuser /app/logs
fi

exec gosu appuser "$@"
