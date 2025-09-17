# Schoology Grade Scraper - Docker Deployment

**Containerized grade monitoring system for ARM64 and x86_64 platforms.**

## Quick Start

```bash
# Clone and setup
git clone https://github.com/yourusername/schoology_scrape.git
cd schoology_scrape
git checkout docker-containerization

# Create required directories and permissions
mkdir -p data logs
sudo chown -R 1000:1000 data logs

# Setup credentials
cp .env.example .env
# Edit .env with your credentials

# Build and test
./docker-build.sh

# Test single run
docker compose -f compose.yaml run --rm --profile manual schoology-scraper
```

## Production Deployment

### Continuous Monitoring (Default)
For automated scheduling with configurable times:

```bash
# Start persistent monitoring (uses SCRAPE_TIMES from .env)
docker compose -f compose.yaml up -d

# Check logs
docker compose -f compose.yaml logs -f

# Stop monitoring
docker compose -f compose.yaml down
```

### Alternative: External Cron Scheduling
For external cron control:
```bash
# Add to crontab (runs daily at 9pm)
crontab -e

# Add this line:
0 21 * * * cd /path/to/schoology_scrape && docker compose -f compose.yaml run --rm --profile manual schoology-scraper
```

## Key Features

### ARM64 Support
- **Chromium-based**: Native ARM64 support (no Chrome compatibility issues)
- **Automatic driver detection**: Finds ChromeDriver in standard Debian/Ubuntu paths
- **Tested on**: Ampere/Graviton ARM64 VPS instances

### Security & Reliability
- **Non-root execution**: Container runs as UID 1000 user
- **Resource limits**: Memory and CPU constraints
- **Comprehensive error handling**: Retry logic with exponential backoff
- **Dual storage**: Local JSON + AWS DynamoDB

### Data Persistence
All data persists across container restarts:
- `./data/` - Grade snapshots and JSON files
- `./logs/` - Application logs
- Configuration files mounted read-only

## Configuration

### Required Files
- `.env` - Credentials (copy from `.env.example`)
- `config.toml` - Application settings (pre-configured)

### Environment Variables
```bash
# Google OAuth (for Schoology login)
evan_google=your-email@gmail.com
evan_google_pw=your-password

# AWS DynamoDB
aws_key=your-access-key
aws_secret=your-secret-key

# Notifications (optional)
pushover_token=your-token
pushover_userkey=your-user-key
gemini_key=your-api-key
```

## Troubleshooting

### Permission Issues
```bash
# Fix volume mount permissions
sudo chown -R 1000:1000 data logs
```

### Debug Container
```bash
# Interactive shell
docker compose run --rm schoology-scraper bash

# Test browser
chromium --version --headless --no-sandbox
```

### View Logs
```bash
# Real-time logs
docker compose logs -f

# Check specific run
ls -la logs/
```

## Architecture

- **Selenium WebDriver**: Chromium + ChromeDriver for ARM64/x86_64
- **Multi-provider notifications**: Pushover, Email, Gemini AI analysis
- **Plugin-based architecture**: Extensible notification system
- **Change detection**: DeepDiff-based grade comparison
- **Cloud storage**: AWS DynamoDB for historical data

Built for reliable, automated grade monitoring on modern VPS platforms.