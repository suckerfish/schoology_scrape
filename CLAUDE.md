# CLAUDE.md

Developer guidance for Claude Code when working with this Schoology grade scraper.

## Project Overview

Automated grade monitoring system: scrapes Schoology → detects changes → sends notifications → stores history.

## Architecture

**Core Pipeline**: Data Fetcher → `pipeline/comparator.py` → `notifications/` → `dynamodb_manager.py`

**Branches:**
- `docker-containerization` - Selenium-based web scraping (stable, production)
- `api-polling` - Schoology API-based polling (faster, experimental)

**Key Directories**:
- `pipeline/` - Data extraction, change detection, orchestration
- `api/` - Schoology API client and fetcher (api-polling branch only)
- `notifications/` - Plugin-based alerts (Pushover, Email, Gemini AI)
- `data/` - Local JSON snapshots (`all_courses_data_YYYYMMDD_HHMMSS.json`)
- `logs/` - Change tracking (`grade_changes.log`, `raw_diffs.log`)

## Configuration

**Environment variables** (`.env`):

**For docker-containerization branch (Selenium scraping):**
- `evan_google`/`evan_google_pw` - Schoology login credentials
- `SCRAPE_TIMES` - Run schedule ("08:00,20:00" for 8am/8pm daily)
- `aws_key`/`aws_secret` - DynamoDB storage
- `pushover_token`/`pushover_userkey` - Mobile notifications
- `gemini_key` - AI analysis

**For api-polling branch (API-based):**
- `SCHOOLOGY_API_KEY` - API key from Schoology developer console
- `SCHOOLOGY_API_SECRET` - API secret from Schoology developer console
- `SCHOOLOGY_DOMAIN` - Your Schoology domain (e.g., lvjusd.schoology.com)
- `SCRAPE_TIMES` - Run schedule (same as above)
- `aws_key`/`aws_secret` - DynamoDB storage (same as above)
- `pushover_token`/`pushover_userkey` - Mobile notifications (same as above)
- `gemini_key` - AI analysis (same as above)

**App settings** (`config.toml`): cache, retries, logging, AWS region

## Data Structure

```
Course → Periods → Categories → Assignments
```

Each assignment: `{title, grade, due_date, comment}`

## Essential Commands

**Docker deployment** (primary):
```bash
docker compose up -d                    # Start monitoring
docker compose logs -f                 # View logs
docker compose down                    # Stop
```

**Note**: This repository is for development only. Production deployment runs from a separate location via git pull.

**Local development**:
```bash
uv pip install -r requirements.txt     # Install deps
python main.py                         # Single run
```

**Testing**:
```bash
python test_pipeline.py                # Validate components
```

## Key Implementation Details

- **Scheduling**: Continuous Docker container sleeps until next `SCRAPE_TIMES`
- **Change Detection**: DeepDiff compares snapshots, triggers notifications only on changes
- **Storage**: Dual persistence (local JSON + DynamoDB) for redundancy
- **Notifications**: Plugin system - providers auto-load based on available credentials
- **Error Handling**: Retry logic with exponential backoff, circuit breakers
- **Docker**: ARM64/x86_64 support, non-root execution, automatic permissions

### Branch-Specific Implementation

**docker-containerization branch:**
- **Data Source**: Selenium WebDriver with Chromium browser
- **Method**: Automated web scraping via Google OAuth login
- **Speed**: ~2-3 minutes per run (browser automation overhead)
- **Reliability**: Subject to UI changes, requires full browser stack
- **Docker Image**: ~500MB with Chromium + dependencies
- **Data Coverage**: 100% of visible grade data including teacher comments

**api-polling branch:**
- **Data Source**: Schoology REST API with OAuth 1.0a authentication
- **Method**: Direct API calls, no browser required
- **Speed**: ~30 seconds per run (API requests only)
- **Reliability**: Stable API contract, less brittle than web scraping
- **Docker Image**: ~800MB (slimmer base with core dependencies)
- **Data Coverage**: ~97.5% (78/80 assignments) - missing 2 assignments, limited teacher comments
- **Known Issue**: Output format differs slightly from scraper, causing false positive change detection (see TODO_API_FORMATTING.md)

## Notification Flow

1. **Comparator** detects changes → formats message
2. **Notification Manager** loads available providers
3. **Gemini Provider** generates AI analysis → adds to metadata
4. **Other providers** (Pushover, Email) send alerts using analysis
5. **Diff Logger** records results in structured JSON

## Recent Changes

- ✅ **Created api-polling branch** - API-based alternative to web scraping (2025-09-30)
  - Replaced Selenium with Schoology REST API
  - ~6x faster execution (30s vs 3min)
  - Removed Chromium dependencies, slimmer base image
  - 97.5% data coverage, missing some comments
  - **TODO**: Fix format mismatches causing false positive notifications
- ✅ **Updated Gemini prompt** to Option 1E style (natural, concise)
- ✅ **Fixed title** from "Grade changes detected" → "Changes detected"
- ✅ **Removed redundant** SCHEDULING.md file

## Development Notes

- Use `uv` for package management
- Always prefer editing existing files over creating new ones
- **Docker Compose file**: This project uses `compose.yaml` (not `docker-compose.yml`)
- Docker Compose uses `pull_policy: build` to avoid duplicate image names
- Keep project root organized - put tests in `tests/` folder
- All optimizations require explicit user approval before implementation