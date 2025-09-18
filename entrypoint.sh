#!/bin/bash
set -e

# Create directories and fix permissions
mkdir -p /app/data /app/logs
chown -R scraper:scraper /app/data /app/logs
chmod 755 /app/data /app/logs

# Switch to non-root user and run the application
exec gosu scraper "$@"