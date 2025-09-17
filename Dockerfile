# syntax=docker/dockerfile:1
# Schoology Grade Scraper - Modern Docker Container

# Use specific Python version with security updates
FROM python:3.12-slim-bookworm AS base

# Metadata labels (OCI standard)
LABEL org.opencontainers.image.title="Schoology Grade Scraper"
LABEL org.opencontainers.image.description="Automated grade monitoring system for Schoology LMS"
LABEL org.opencontainers.image.version="3.0"
LABEL org.opencontainers.image.source="https://github.com/yourusername/schoology_scrape"
LABEL org.opencontainers.image.licenses="MIT"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DISPLAY=:99

# Install system dependencies in single layer
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    # Core utilities
    wget=1.21.3-1+deb12u2 \
    curl=7.88.1-10+deb12u8 \
    unzip=6.0-28 \
    xvfb=2:21.1.7-3+deb12u7 \
    # Security
    ca-certificates=20230311 \
    gnupg=2.2.40-1.1 \
    gpg=2.2.40-1.1 \
    # Chromium and dependencies
    chromium=119.0.6045.199-1~deb12u1 \
    chromium-driver=119.0.6045.199-1~deb12u1 \
    # Font and display libraries
    fonts-liberation=1:2.1.5-1 \
    libasound2=1.2.8-1+b1 \
    libatk-bridge2.0-0=2.46.0-5 \
    libatk1.0-0=2.46.0-5 \
    libatspi2.0-0=2.46.0-5 \
    libcups2=2.4.2-3+deb12u5 \
    libdbus-1-3=1.14.10-1~deb12u1 \
    libdrm2=2.4.114-1+b1 \
    libgbm1=22.3.6-1+deb12u1 \
    libgtk-3-0=3.24.38-2~deb12u1 \
    libgtk-4-1=4.8.3+ds-2 \
    libnspr4=2:4.35-1 \
    libnss3=2:3.87.1-1+deb12u1 \
    libwayland-client0=1.21.0-1 \
    libxcomposite1=1:0.4.5-1 \
    libxdamage1=1:1.1.6-1 \
    libxfixes3=1:6.0.0-2 \
    libxkbcommon0=1.5.0-1 \
    libxrandr2=2:1.5.2-2+b1 \
    xdg-utils=1.1.3-4.1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y \
    && apt-get autoclean

# Create non-root user first (security best practice)
RUN groupadd --gid 1000 scraper \
    && useradd --uid 1000 --gid scraper --shell /bin/bash --create-home scraper

# Set working directory
WORKDIR /app

# Create directories with proper permissions
RUN mkdir -p /app/{data,logs,cache} \
    && chown -R scraper:scraper /app

# Copy requirements first (better layer caching)
COPY --chown=scraper:scraper schoology-scraper/requirements.txt ./

# Install Python dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/pip,uid=1000,gid=1000 \
    pip install --no-cache-dir --upgrade pip==24.0 \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=scraper:scraper . .

# Switch to non-root user
USER scraper:scraper

# Health check with more specific test
HEALTHCHECK --interval=60s --timeout=30s --start-period=120s --retries=3 \
    CMD python -c "import sys; from selenium import webdriver; sys.exit(0)" || exit 1

# Expose no ports (this is a background service)
EXPOSE

# Use exec form for proper signal handling
CMD ["python", "-u", "main.py"]