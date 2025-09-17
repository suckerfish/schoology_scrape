# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm as base

# Configure environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=America/Los_Angeles \
    DISPLAY=:99

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl unzip xvfb ca-certificates gnupg \
    chromium chromium-driver \
    fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libatspi2.0-0 libcups2 libdbus-1-3 libdrm2 libgbm1 \
    libgtk-3-0 libnspr4 libnss3 libwayland-client0 \
    libxcomposite1 libxdamage1 libxfixes3 libxkbcommon0 \
    libxrandr2 xdg-utils \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y \
    && apt-get autoclean

# Create non-root user
RUN groupadd --gid 1000 scraper \
    && useradd --uid 1000 --gid scraper --shell /bin/bash --create-home scraper

# Set up application directory
WORKDIR /app
RUN mkdir -p /app/{data,logs,cache} \
    && chown -R scraper:scraper /app

# Copy requirements and install Python dependencies
COPY --chown=scraper:scraper requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=scraper:scraper . .

# Switch to non-root user
USER scraper:scraper

# Health check
HEALTHCHECK --interval=60s --timeout=30s --start-period=120s --retries=3 \
    CMD python -c "import sys; from selenium import webdriver; sys.exit(0)" || exit 1

# No ports to expose (background service)

# Run the application
CMD ["python", "-u", "main.py"]