#!/bin/bash
set -e

# Ensure directories exist (mkdir -p is safe if already present)
mkdir -p /app/data /app/logs || true

# Fix ownership only if writable (avoids failures on read-only mounts)
for d in /app/data /app/logs; do
  if [ -d "$d" ]; then
    if [ -w "$d" ]; then
      chown -R scraper:scraper "$d" || true
      chmod 755 "$d" || true
    else
      echo "[entrypoint] $d is read-only; skipping ownership changes"
    fi
  fi
done

# Switch to non-root user and run the application
exec gosu scraper "$@"
