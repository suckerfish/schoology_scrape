# Schoology Grade Scraper - Docker Deployment

This document explains how to run the Schoology Grade Scraper in Docker containers.

## Quick Start

1. **Build and run once:**
   ```bash
   docker-compose up --build
   ```

2. **For scheduled runs (every hour):**
   ```bash
   docker-compose --profile scheduler up --build
   ```

## Setup Requirements

### 1. Create Required Directories
```bash
mkdir -p data logs
```

### 2. Configuration Files
Ensure these files exist in your project root:
- `config.toml` - Application settings
- `.env` - Credentials (Google, AWS, Pushover, Gemini keys)

### 3. File Permissions
```bash
# Ensure the container user can write to data/logs directories
chmod 755 data logs
```

## Deployment Options

### Option 1: One-Shot Execution
Run the scraper once and exit:
```bash
docker-compose up
```

### Option 2: Scheduled Service
Run continuously with hourly scraping:
```bash
docker-compose --profile scheduler up -d
```

### Option 3: External Cron Job
Set up a cron job on your VPS:
```bash
# Add to crontab: run every hour at minute 0
0 * * * * cd /path/to/schoology_scrape && docker-compose up --abort-on-container-exit
```

## Data Persistence

The following directories are mounted as volumes:
- `./data` → `/app/data` - Grade snapshots and JSON files
- `./logs` → `/app/logs` - Application logs
- `./config.toml` → `/app/config.toml` (read-only)
- `./.env` → `/app/.env` (read-only)

## Container Features

### Security
- Runs as non-root user (`scraper`)
- No new privileges flag set
- Resource limits configured
- Read-only configuration mounts

### Monitoring
- Health check endpoint
- Structured logging with rotation
- Resource monitoring available via `docker stats`

### Chrome/Selenium
- Google Chrome stable pre-installed
- All Chrome dependencies included
- Headless mode with virtual display
- Optimized for containerized environments

## Troubleshooting

### Check Container Status
```bash
docker-compose ps
docker-compose logs
```

### Debug Chrome Issues
```bash
# Run container interactively
docker-compose run --rm schoology-scraper bash

# Test Chrome installation
google-chrome --version --headless --no-sandbox
```

### Monitor Resources
```bash
docker stats schoology-scraper
```

### Clean Up
```bash
# Stop and remove containers
docker-compose down

# Remove images
docker-compose down --rmi all

# Clean up volumes (CAUTION: deletes data)
docker-compose down -v
```

## Production Deployment

For production VPS deployment:

1. **Use specific image tags:**
   ```yaml
   image: schoology-scraper:v1.0.0
   ```

2. **Configure log aggregation:**
   ```yaml
   logging:
     driver: syslog
     options:
       syslog-address: "tcp://your-log-server:514"
   ```

3. **Set up monitoring:**
   - Container health checks
   - Log monitoring for errors
   - Resource usage alerts

4. **Backup strategy:**
   - Regular backup of `./data` directory
   - Configuration file backups
   - Database snapshots (DynamoDB)

## Environment Variables

All sensitive configuration is handled via `.env` file:
- `evan_google` / `evan_google_pw` - Google credentials
- `aws_key` / `aws_secret` - AWS DynamoDB access
- `pushover_token` / `pushover_userkey` - Notifications
- `gemini_key` - AI analysis API key