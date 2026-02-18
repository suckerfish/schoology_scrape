# Technology Stack

**Analysis Date:** 2026-02-14

## Languages

**Primary:**
- Python 3.12 - Core application, API client, and orchestration
- Shell (bash) - Entrypoint scripts and Docker build automation

## Runtime

**Environment:**
- Python 3.12-slim-bookworm (Docker image)

**Package Manager:**
- pip (bundled with Python)
- Lockfile: `requirements.txt` (present but unpinned versions with minimum requirements)

## Frameworks

**Core:**
- None - This is a standalone Python application without a web framework

**API Client:**
- `requests` 2.31.0+ - HTTP requests library
- `requests-oauthlib` 1.3.1+ - OAuth 1.0a authentication for Schoology API

**Data Handling:**
- `toml` 0.10.2+ - Configuration file parsing
- `python-dotenv` 1.0.0+ - Environment variable loading from `.env`

**AI/ML:**
- `google-genai` 1.0.0+ - Google Gemini API for AI-powered grade analysis
- `absl-py` 2.0.0+ - Python logging utilities (dependency for google-genai)

**Testing:**
- `pytest` 7.4.0+ - Unit testing framework

**Build/Dev:**
- Docker (containerization)

## Key Dependencies

**Critical:**
- `requests-oauthlib` 1.3.1+ - OAuth 1.0a authentication to Schoology API; without this, cannot authenticate to fetch grades
- `python-dotenv` 1.0.0+ - Credential and configuration loading; application will not start without proper env var handling
- `google-genai` 1.0.0+ - Gemini AI analysis; required for optional AI-powered notifications (conditional import)

**Infrastructure:**
- `sqlite3` (stdlib) - Local database for grade state storage and change detection
- `smtplib` (stdlib) - Email provider via Gmail SMTP
- `urllib.request` (stdlib) - Healthchecks.io HTTP pings for uptime monitoring

## Configuration

**Environment:**
- `.env` file (user-provided) - Contains API keys, secrets, credentials
- `config.toml` - Application settings (log level, retry behavior, storage settings)
- Configured via `shared/config.py` using dataclass-based configuration objects

**Key env vars required:**
- `SCHOOLOGY_API_KEY` - Schoology API key
- `SCHOOLOGY_API_SECRET` - Schoology API secret
- `SCHOOLOGY_DOMAIN` - Schoology instance domain (e.g., yourschool.schoology.com)
- `SCRAPE_TIMES` - Comma-separated 24h format times for scheduling (e.g., "08:00,20:00")

**Optional env vars:**
- `gemini_key` - Google Gemini API key for grade analysis
- `email_sender`, `email_password`, `email_receiver` - Gmail SMTP notifications
- `aws_key`, `aws_secret` - AWS DynamoDB storage (optional, not actively used)
- `HEALTHCHECKS_URL` - Healthchecks.io uptime monitoring ping URL

**Build Configuration:**
- `Dockerfile` - Containerization with Python 3.12-slim-bookworm
- `compose.yaml` - Single service definition pulling from GHCR
- `.github/workflows/docker-publish.yml` - CI pipeline: multi-arch build (amd64 + arm64) → GHCR
- `.dockerignore` - Docker build context filtering

## Platform Requirements

**Development:**
- Python 3.12+ (local development)
- Docker + Docker Compose (containerized deployment)
- Virtual environment (recommended via `uv` per project preferences in CLAUDE.md)

**Production:**
- Docker runtime environment
- Access to external APIs:
  - Schoology API endpoint (OAuth 1.0a)
  - Google Gemini API (optional, for AI analysis)
  - Gmail SMTP server (optional, for email notifications)
  - Healthchecks.io (optional, for uptime monitoring)
  - GHCR (`ghcr.io`) for pulling container image
- Network connectivity to all integrated services
- Local SQLite database persistence (volume mount in Docker Compose)

## Data Storage

**Local:**
- `data/grades.db` - SQLite database for grade snapshots and change detection
- `logs/grade_scraper.log` - Application logs
- `logs/scheduler.log` - Scheduler logs
- `logs/grade_changes.log` - JSON change event logs (with retention policy: 90 days default)

**Cloud (optional):**
- AWS DynamoDB - Configuration exists but not actively used per code analysis
- Google Gemini API - Cloud-based AI analysis service

## Scheduling

**Daemon Mode:**
- `main.py --daemon` - Runs continuously at configured times
- `scheduler.py` - Alternative scheduler (used in Docker Compose)
- Both support `SCRAPE_TIMES` environment variable for multi-run daily scheduling

---

*Stack analysis: 2026-02-14*
