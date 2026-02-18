# External Integrations

**Analysis Date:** 2026-02-14

## APIs & External Services

**Grade Data Source:**
- Schoology REST API - Primary source for grade data retrieval
  - SDK/Client: Custom `SchoologyAPIClient` in `api/client.py`
  - Auth: OAuth 1.0a (via `requests-oauthlib`)
  - Env vars: `SCHOOLOGY_API_KEY`, `SCHOOLOGY_API_SECRET`, `SCHOOLOGY_DOMAIN`
  - Base URL: `https://api.schoology.com/v1`
  - Endpoints used:
    - `users/me` - Get current user ID
    - `users/{uid}/sections` - Get all course sections for user
    - `users/{uid}/grades` - Get grades for all sections or specific section

**AI Analysis:**
- Google Gemini API - AI-powered grade change analysis
  - SDK/Client: `google-genai` package (`google.genai.Client`)
  - Auth: API key (env var `gemini_key`)
  - Model used: `gemini-2.0-flash`
  - Provider implementation: `notifications/gemini_provider.py`
  - Optional: Only active if `gemini_key` is configured
  - Usage: Generates natural language summaries of grade changes for notifications

**Uptime Monitoring:**
- Healthchecks.io - Monitors scraper execution health
  - Integration: HTTP ping (via `urllib.request`)
  - Env var: `HEALTHCHECKS_URL` (full ping URL)
  - Behavior: Pings on both success and failure
  - Implementation: `pipeline/orchestrator_v2.py` - `_ping_healthchecks_io()` method
  - Optional: Only active if `HEALTHCHECKS_URL` is configured

## Data Storage

**Databases:**
- SQLite (local file-based)
  - Connection: `data/grades.db` (file path)
  - Client: Python stdlib `sqlite3`
  - ORM/Client: Direct SQL via context managers in `shared/grade_store.py`
  - Schema:
    - `snapshots` - Metadata about grade data snapshots
    - `sections` - Course sections
    - `periods` - Grading periods within sections
    - `categories` - Grading categories within periods
    - `assignments` - Individual assignments with grades and IDs
  - Purpose: Efficient ID-based change detection (replaced JSON file snapshots)

**File Storage:**
- Local filesystem only
  - Grade database: `data/grades.db`
  - Logs: `logs/` directory
  - Config: `config.toml` (application settings)
  - Change journal: `logs/grade_changes.log` (JSON format, 90-day retention)

**Caching:**
- None - Caching is handled in-process only (no Redis or Memcached)
- TTL configuration exists in `config.toml` but not actively used for external caching

## Authentication & Identity

**Auth Provider:**
- Custom OAuth 1.0a (Schoology API)
  - Implementation: `api/client.py` - `SchoologyAPIClient` class
  - Approach: Uses `requests-oauthlib.OAuth1Session` with API key and secret
  - Credentials sourced from env vars: `SCHOOLOGY_API_KEY`, `SCHOOLOGY_API_SECRET`
  - No external identity provider (all credentials stored locally in `.env`)

## Monitoring & Observability

**Error Tracking:**
- None - No external error tracking service (Sentry, Rollbar, etc.)
- Local error handling with logging fallback

**Logs:**
- Local file-based logging
  - `logs/grade_scraper.log` - Application runtime logs
  - `logs/scheduler.log` - Scheduler logs
  - `logs/grade_changes.log` - JSON format change events (structured logging)
- Format: Text-based with timestamps and log levels
- Retention: 90 days for change logs (configurable in `config.toml`), unlimited for runtime logs

**Health Checks:**
- Healthchecks.io integration (optional)
  - Pings on every pipeline run
  - Success ping: Indicates grades fetched successfully
  - Failure ping: Indicates pipeline error
  - See: `pipeline/orchestrator_v2.py` - `_ping_healthchecks_io()` method

## CI/CD & Deployment

**Hosting:**
- Docker (self-hosted or cloud container platform)
- Container image: `ghcr.io/suckerfish/schoology_scrape:latest` (multi-arch: amd64 + arm64)
- Entry point: `scheduler.py` (runs indefinitely at scheduled times)
- Alternative entry: `main.py` (single run or daemon mode)

**CI Pipeline:**
- GitHub Actions (`.github/workflows/docker-publish.yml`)
  - Triggers on push to `main`
  - Builds multi-platform Docker image (linux/amd64, linux/arm64) via QEMU + Buildx
  - Pushes to GitHub Container Registry (ghcr.io)
  - Tags: `latest` + commit SHA

**Deployment:**
- Docker Compose (`compose.yaml`)
  - Service: `schoology-scheduler`
  - Image: `ghcr.io/suckerfish/schoology_scrape:latest`
  - Command: `python scheduler.py`
  - Volumes: data/, logs/
  - Restart policy: `unless-stopped`
  - Environment: Loaded from `.env` file

## Notification Services

**Email Notifications:**
- Gmail SMTP - Email notifications via Gmail
  - SMTP server: `smtp.gmail.com` (port 587)
  - Auth: Email + App-specific password (not regular password)
  - Env vars: `email_sender`, `email_password`, `email_receiver`
  - Provider implementation: `notifications/email_provider.py`
  - Features: HTML/plain text, multiple recipients (comma-separated), file attachments
  - Transport: TLS
  - Optional: Only active if all email credentials are configured

## Notification Orchestration

**Notification System:**
- Plugin-based manager in `notifications/manager.py`
- Supported providers: Email, Gemini (AI analysis)
- Auto-loading: Providers load only if credentials are present
- Execution order: Gemini runs first (generates AI analysis), then other providers use enhanced message
- Message enrichment: Gemini analysis added to message metadata for other providers
- Base class: `NotificationProvider` (abstract in `notifications/base.py`)

## Environment Configuration

**Required env vars:**
- `SCHOOLOGY_API_KEY` - Schoology API authentication
- `SCHOOLOGY_API_SECRET` - Schoology API authentication
- `SCHOOLOGY_DOMAIN` - Schoology instance (e.g., yourschool.schoology.com)
- `SCRAPE_TIMES` - Schedule in 24h format (e.g., "08:00,20:00")

**Optional env vars (service integrations):**
- `email_sender`, `email_password`, `email_receiver` - Email notifications
- `gemini_key` - AI analysis
- `aws_key`, `aws_secret` - AWS (optional, not actively used)
- `HEALTHCHECKS_URL` - Uptime monitoring

**Secrets location:**
- `.env` file (local, git-ignored)
- Docker Compose loads from `.env` via `env_file` directive
- Never commit `.env` to version control

## Webhooks & Callbacks

**Incoming:**
- None - This application is a client only, does not expose HTTP endpoints

**Outgoing:**
- Schoology API - REST API calls to fetch grade data (polling, not event-driven)
- Google Gemini API - REST API calls for AI analysis
- Gmail SMTP - SMTP protocol for email notifications
- Healthchecks.io - HTTP GET request to ping endpoint

## Data Model Integration

**API Response Structure:**
- Schoology API returns nested JSON: `GradeData > Section > Period > Category > Assignment`
- Parsed into Pydantic models: `shared/models.py`
  - `GradeData` - Root container
  - `Section` - Course section
  - `Period` - Grading period (e.g., "Term 1")
  - `Category` - Grade category (e.g., "Homework")
  - `Assignment` - Individual assignment with earned/max points

**Change Detection Flow:**
1. API fetcher (`api/fetch_grades_v2.py`) → Pydantic models
2. ID Comparator (`shared/id_comparator.py`) → compares against SQLite state
3. Change Logger (`shared/change_logger.py`) → writes JSON to `logs/grade_changes.log`
4. Notification Manager → routes to all available providers
5. SQLite Store (`shared/grade_store.py`) → persists new state

---

*Integration audit: 2026-02-14*
