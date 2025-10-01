# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm as base

# Configure environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=America/Los_Angeles

# Install minimal system dependencies (CA certs + gosu for non-root execution)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates gosu \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y \
    && apt-get autoclean

# Set up application directory
WORKDIR /app

# Create non-root user
RUN groupadd --gid 1000 scraper \
    && useradd --uid 1000 --gid scraper --shell /bin/bash --create-home scraper \
    && mkdir -p /app/data /app/logs /app/cache \
    && chown -R scraper:scraper /app \
    && chmod 755 /app/logs

# Copy requirements and install Python dependencies
COPY --chown=scraper:scraper requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=scraper:scraper . .

# Copy and set up entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Health check
HEALTHCHECK --interval=60s --timeout=30s --start-period=120s --retries=3 \
    CMD python -c "import sys; import requests; sys.exit(0)" || exit 1

# No ports to expose (background service)

# Run the application
CMD ["python", "-u", "main.py"]