# CLAUDE.md

Developer guidance for Claude Code when working with this Schoology grade scraper.

## Project Overview

Automated grade monitoring system: polls Schoology API → detects changes via ID-based comparison → sends notifications → stores state in SQLite.

## Architecture

**Core Pipeline**: `api/fetch_grades_v2.py` → `shared/id_comparator.py` → `notifications/` → `shared/grade_store.py`

**Key Directories**:
- `api/` - Schoology API client and grade fetcher
- `pipeline/` - Orchestration (`orchestrator_v2.py`)
- `shared/` - Core modules (models, comparator, store, config)
- `notifications/` - Plugin-based alerts (Pushover, Email, Gemini AI)
- `data/` - SQLite database (`grades.db`) and logs
- `logs/` - Change tracking (`grade_changes.log`)
- `tests/` - Unit tests

## Configuration

**Environment variables** (`.env`):
- `SCHOOLOGY_API_KEY` - API key from Schoology
- `SCHOOLOGY_API_SECRET` - API secret from Schoology
- `SCHOOLOGY_DOMAIN` - Your Schoology domain (e.g., lvjusd.schoology.com)
- `SCRAPE_TIMES` - Run schedule ("08:00,20:00" for 8am/8pm daily)
- `aws_key`/`aws_secret` - DynamoDB storage (optional)
- `pushover_token`/`pushover_userkey` - Mobile notifications
- `gemini_key` - AI analysis
- `HEALTHCHECKS_URL` - Uptime monitoring (pings on each run)

**App settings** (`config.toml`): retries, logging, AWS region

## Data Model

```python
GradeData → Section → Period → Category → Assignment
```

Each assignment has: `assignment_id`, `title`, `earned_points`, `max_points`, `exception`, `comment`, `due_date`

State stored in SQLite (`data/grades.db`) with tables: `snapshots`, `sections`, `periods`, `categories`, `assignments`

## Essential Commands

**Docker deployment**:
```bash
docker compose up -d        # Start monitoring
docker compose logs -f      # View logs
docker compose down         # Stop
```

**Local development**:
```bash
uv pip install -r requirements.txt  # Install deps
python main.py                      # Single run
python -m pytest tests/ -v          # Run tests
```

## Key Implementation Details

- **Data Source**: Schoology REST API with OAuth 1.0a (`api/fetch_grades_v2.py`)
- **Change Detection**: ID-based comparison using SQLite (`shared/id_comparator.py`)
- **State Storage**: SQLite database (`shared/grade_store.py`)
- **Models**: Pydantic models with type validation (`shared/models.py`)
- **Logging**: JSON change logs (`shared/change_logger.py`)
- **Scheduling**: Continuous Docker container sleeps until next `SCRAPE_TIMES`
- **Notifications**: Plugin system - providers auto-load based on available credentials

## Notification Flow

1. **Orchestrator** runs pipeline → fetches grades via API
2. **IDComparator** compares against SQLite state → generates ChangeReport
3. **ChangeLogger** writes JSON to `logs/grade_changes.log`
4. **Notification Manager** loads available providers
5. **Gemini Provider** generates AI analysis → adds to metadata
6. **Other providers** (Pushover, Email) send alerts

## Recent Changes

- Added healthchecks.io integration for uptime monitoring
- Removed "no changes" status notifications (only notifies on actual grade changes)
- Migrated to ID-based change detection (replaced DeepDiff)
- SQLite state storage (replaced JSON snapshot comparison)
- New Gemini SDK (`google-genai` replacing deprecated `google-generativeai`)
- Simplified to single branch (main)
- Removed Selenium/browser scraping (API-only now)

## Development Notes

- Use `uv` for package management
- Always prefer editing existing files over creating new ones
- **Docker Compose file**: This project uses `compose.yaml` (not `docker-compose.yml`)
- Keep project root organized - put tests in `tests/` folder
- All optimizations require explicit user approval before implementation

## Known Limitations

- ~5 assignments return 403 Forbidden (Schoology API permission issue)
- Section ID offset matching sometimes needed (handled automatically)
- Teacher comments limited compared to web scraping
