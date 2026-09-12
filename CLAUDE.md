# CLAUDE.md

Developer guidance for Claude Code when working with this Schoology grade scraper.

## Project Overview

Automated grade monitoring system: polls Schoology API → detects changes via ID-based comparison → sends notifications → stores state in SQLite.

## Architecture

**Core Pipeline**: `api/fetch_grades_v2.py` → `shared/id_comparator.py` → `notifications/` → `shared/grade_store.py`

**Key Directories**:
- `api/` - Schoology API client and grade fetcher
- `pipeline/` - Orchestration (`orchestrator_v2.py`) and notification coordination (`notifier.py`)
- `shared/` - Core modules (models, comparator, store, config)
- `notifications/` - Plugin-based alerts (Email, Gemini AI)
- `data/` - SQLite database (`grades.db`) and logs
- `logs/` - Change tracking (`grade_changes.log`)
- `tests/` - Unit tests

## Configuration

**Environment variables** (`.env`):
- `SCHOOLOGY_API_KEY` - API key from Schoology
- `SCHOOLOGY_API_SECRET` - API secret from Schoology
- `SCRAPE_TIMES` - Run schedule ("08:00,20:00" for 8am/8pm daily)
- `gemini_key` - AI analysis (optional)
- `email_sender`/`email_password`/`email_receiver` - Email notifications (optional)
- `HEALTHCHECKS_URL` - Uptime monitoring (pings on each run, optional)

**App settings** (`config.toml`): log level, retries, data directory, change-log retention,
email toggle, grade-history toggle and snapshot retention

## Data Model

```python
GradeData → Section → Period → Category → Assignment
```

Each assignment has: `assignment_id`, `title`, `earned_points`, `max_points`, `exception`, `comment`, `due_date`

State stored in SQLite (`data/grades.db`) with tables: `snapshots`, `sections`, `periods`,
`categories`, `assignments`, `assignment_history`, `assignment_meta`

`assignments` holds current state only (upserts overwrite). `assignment_history` is
append-only — one row per assignment per snapshot — and is what time-series dashboards
read. `assignment_meta` keeps each assignment's labels (title, course, period, category)
so a series stays readable after its section is pruned. History rows hang off
`snapshots` with `ON DELETE CASCADE`, so `[history] retention_snapshots` in `config.toml`
is the real history retention knob (0 = keep everything).

Writes are upserts, not `INSERT OR REPLACE`: foreign keys are enforced with
`ON DELETE CASCADE`, so a REPLACE would cascade-delete a row's children. Sections
missing from the API feed are pruned on save (skipped if the feed is empty), and
the `snapshots` table is capped by `[history] retention_snapshots` (0 = uncapped).

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

**Backfill grade history** (recovers pre-history data from the change log):
```bash
python scripts/backfill_history.py --dry-run   # report what would be written
python scripts/backfill_history.py             # write it
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
6. **Email provider** sends alerts

## Recent Changes

- Added `assignment_history` / `assignment_meta` for point-in-time grades, plus
  `get_assignment_history()`, `get_history_at()` and `get_snapshot_times()` for scrubbing
  dashboards; `scripts/backfill_history.py` replays `grade_changes.log` into it
- Snapshots are ordered by `timestamp`, not `id`, since backfill inserts historical rows last
- Section IDs are resolved by direct `/sections/{id}` lookup and joined to enrollments on `course_id`; detail endpoints try both IDs
- Assignments are fetched per section in one bulk call, with a per-assignment fallback
- Removed dead code: `pipeline/error_handling.py`, unused notification/config/store methods, orphaned config keys
- Logging is configured once in `main.py` (no module-level `basicConfig`) and the file log rotates at 5 MB
- Added `pydantic` to `requirements.txt`; dropped unused `absl-py` and `toml`
- Sanitized codebase for public repository (removed hardcoded domain, legacy Google login fields)
- Docker image published to GHCR (`ghcr.io/suckerfish/schoology_scrape`) via GitHub Actions (multi-arch: amd64 + arm64)
- `compose.yaml` pulls from GHCR instead of building locally
- Added healthchecks.io integration for uptime monitoring
- Removed "no changes" status notifications (only notifies on actual grade changes)
- Removed Pushover notifications
- Migrated to ID-based change detection (replaced DeepDiff)
- SQLite state storage (replaced JSON snapshot comparison)
- New Gemini SDK (`google-genai` replacing deprecated `google-generativeai`)
- Removed Selenium/browser scraping (API-only now)

## CI/CD

- **GitHub Actions**: `.github/workflows/docker-publish.yml` builds and pushes multi-arch Docker images (amd64 + arm64) to GHCR on every push to `main`
- **Image**: `ghcr.io/suckerfish/schoology_scrape:latest`

## Development Notes

- Use `uv` for package management
- Always prefer editing existing files over creating new ones
- **Docker Compose file**: This project uses `compose.yaml` (not `docker-compose.yml`)
- Keep project root organized - put tests in `tests/` folder
- All optimizations require explicit user approval before implementation

## Known Limitations

- A section may deny detail endpoints on one of its two IDs; the fetcher retries with the other
- Teacher comments limited compared to web scraping
