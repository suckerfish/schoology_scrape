# CLAUDE.md

Developer guidance for Claude Code when working with this Schoology grade scraper.

## Project Overview

Automated grade monitoring system: scrapes Schoology → detects changes → sends notifications → stores history.

## Architecture

**Core Pipeline**: `pipeline/scraper.py` → `pipeline/comparator.py` → `notifications/` → `dynamodb_manager.py`

**Key Directories**:
- `pipeline/` - Data extraction, change detection, orchestration
- `notifications/` - Plugin-based alerts (Pushover, Email, Gemini AI)
- `data/` - Local JSON snapshots (`all_courses_data_YYYYMMDD_HHMMSS.json`)
- `logs/` - Change tracking (`grade_changes.log`, `raw_diffs.log`)
- `pages/` - Streamlit dashboard components

## Configuration

**Environment variables** (`.env`):
- `evan_google`/`evan_google_pw` - Schoology login credentials
- `SCRAPE_TIMES` - Run schedule ("08:00,20:00" for 8am/8pm daily)
- `aws_key`/`aws_secret` - DynamoDB storage
- `pushover_token`/`pushover_userkey` - Mobile notifications
- `gemini_key` - AI analysis

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
streamlit run streamlit_viewer.py      # Dashboard
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

## Notification Flow

1. **Comparator** detects changes → formats message
2. **Notification Manager** loads available providers
3. **Gemini Provider** generates AI analysis → adds to metadata
4. **Other providers** (Pushover, Email) send alerts using analysis
5. **Diff Logger** records results in structured JSON

## Recent Changes

- ✅ **Updated Gemini prompt** to Option 1E style (natural, concise)
- ✅ **Fixed title** from "Grade changes detected" → "Changes detected"
- ✅ **Removed redundant** SCHEDULING.md file

## Development Notes

- Use `uv` for package management
- Always prefer editing existing files over creating new ones
- Docker Compose uses `pull_policy: build` to avoid duplicate image names
- Keep project root organized - put tests in `tests/` folder
- All optimizations require explicit user approval before implementation