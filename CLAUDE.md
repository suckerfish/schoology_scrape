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
- `DATASETTE_BIND` - Host IP for the Datasette port (default `127.0.0.1`; a Tailscale IP in production)

**App settings** (`config.toml`): log level, retries, data directory, change-log retention, email toggle

## Data Model

```python
GradeData → Section → Period → Category → Assignment
```

Sections carry `course_grade`/`course_letter`, periods carry `grade`/`letter`, and
categories carry `grade`. These are the values Schoology reports in the grades
feed's `final_grade` array (`period_id: 'final'` is the course grade). The API
returns them even when the web GUI hides a grade, so nothing is computed locally.

Each assignment has: `assignment_id`, `title`, `earned_points`, `max_points`, `exception`, `comment`, `due_date`, `graded_at` (when the grade was entered; not used for change detection)

`exception` holds the Schoology grade mark. Codes 1-3 (Excused, Incomplete, Missing) replace
the score. Codes 4 (Collected) and 6 (Late), both confirmed in the GUI, keep
the score, and `grade_string()` shows them as `4 / 10 (Late)`. Unknown codes are stored as
`Mark <code>`, never dropped.

State stored in SQLite (`data/grades.db`) with tables: `snapshots`, `sections`, `periods`, `categories`, `assignments`, `grade_history`

`grade_history` is append-only: one row (`kind` = course/period/category/assignment)
each time a stored grade changes, including its first value. It has no foreign
keys, so it survives section pruning.

Writes are upserts, not `INSERT OR REPLACE`: foreign keys are enforced with
`ON DELETE CASCADE`, so a REPLACE would cascade-delete a row's children. Sections
missing from the API feed are pruned on save (skipped if the feed is empty), and
the `snapshots` table is capped at 100 rows.

## Querying the Database (Datasette)

The `datasette` service in `compose.yaml` serves `data/grades.db` read-only on port 8001
(image built from `datasette/Dockerfile`, because the official image is amd64-only).
Canned queries live in `datasette/metadata.yml`; edit that file when the schema changes.
Grade data is private: bind only to `DATASETTE_BIND`, never publicly.

Prefer the JSON API over SSH + sqlite3 for ad-hoc questions and dashboards:
- `/grades.json?sql=SELECT...&_shape=array` - any read-only SELECT
- `/grades/<table>.json?_shape=array` - table rows (supports `?col=value` filters)
- `/grades/<canned_query>.json?param=...&_shape=array` - `class_grades`, `course_trend`
  (`course`), `recent_changes` (`days`), `recent_assignment_changes` (`days`), `missing_or_zero`,
  `grade_revisions` (late turn-ins, regrades, marks added), `assignment_timeline` (`assignment`),
  `late_or_collected`

Course, period, and category history starts on 2026-10-14. Assignment history goes back to
2026-08-14, because `python main.py --backfill-history` copied older changes from
`logs/grade_changes.log` (90-day retention). The backfill is idempotent.

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
python main.py --report             # Print stored grade snapshot (no API calls)
python main.py --backfill-history   # Copy older change-log entries into grade_history (idempotent)
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
2. **IDComparator** compares against SQLite state → generates ChangeReport (assignment changes plus course/period `class_changes`)
3. **ChangeLogger** writes JSON to `logs/grade_changes.log`
4. **Notification Manager** loads available providers
5. **Gemini Provider** generates AI analysis → adds to metadata
6. **Email provider** sends alerts

## Recent Changes

- Grade marks 4 (Collected) and 6 (Late) are stored instead of dropped; they keep the score
- `--backfill-history` copies pre-`grade_history` assignment changes from the change log
- Read-only Datasette service (`datasette/`) with canned queries, bound to `DATASETTE_BIND`
- Course, period, and category grades parsed from `final_grade`, stored, and tracked in `grade_history`; class grade changes are notified and `--report` prints the snapshot
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
