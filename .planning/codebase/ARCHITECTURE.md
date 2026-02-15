# Architecture

**Analysis Date:** 2026-02-14

## Pattern Overview

**Overall:** Modular pipeline with ID-based change detection and plugin notification system.

**Key Characteristics:**
- **Separation of concerns**: Discrete layers for API access, data comparison, storage, and notifications
- **Event-driven notifications**: Pipeline detects changes and triggers pluggable notification providers
- **State-based change detection**: Compares using unique identifiers stored in SQLite, not deep object comparison
- **Containerized scheduler**: Runs in Docker with configurable scrape times; orchestrates via daemon or single-run modes

## Layers

**API Layer:**
- Purpose: Fetch grade data from Schoology REST API using OAuth 1.0a authentication
- Location: `api/`
- Contains: `SchoologyAPIClient` (auth and HTTP), `APIGradeFetcherV2` (orchestrates API calls and model building)
- Depends on: `requests_oauthlib`, environment credentials
- Used by: `GradePipelineV2` for data retrieval

**Data Model Layer:**
- Purpose: Normalize and validate grade structures with stable unique identifiers
- Location: `shared/models.py`
- Contains: `Assignment`, `Category`, `Period`, `Section`, `GradeData` Pydantic models
- Depends on: `pydantic`, `decimal.Decimal` for numeric precision
- Used by: All other layers for type-safe grade data representation

**Persistence Layer:**
- Purpose: Store and retrieve grade snapshots using SQLite with ID-based lookups
- Location: `shared/grade_store.py`
- Contains: `GradeStore` class managing `snapshots`, `sections`, `periods`, `categories`, `assignments` tables
- Depends on: `sqlite3`, database file at `data/grades.db`
- Used by: `IDComparator` for historical state lookups

**Comparison Layer:**
- Purpose: Detect grade changes by comparing current API data against stored snapshots using unique IDs
- Location: `shared/id_comparator.py`
- Contains: `IDComparator` (detects changes), `GradeChange` (represents single change), `ChangeReport` (aggregates changes)
- Depends on: `GradeStore` for historical data, `GradeData` models
- Used by: `GradePipelineV2` to determine if notifications should be sent

**Notification Layer:**
- Purpose: Plugin architecture for delivering notifications via multiple channels
- Location: `notifications/`
- Contains: `NotificationProvider` (abstract base), `NotificationManager` (loads providers), provider implementations (Pushover, Email, Gemini)
- Depends on: External APIs (Pushover, SendGrid/SMTP, Google Generative AI)
- Used by: `GradeNotifier` which is called by `GradePipelineV2`

**Change Logging Layer:**
- Purpose: Record all detected changes as structured JSON history for auditing and analysis
- Location: `shared/change_logger.py`
- Contains: `ChangeLogger` class writing to `logs/grade_changes.log`
- Depends on: `pathlib`, JSON serialization
- Used by: `GradePipelineV2` for historical tracking

**Configuration Layer:**
- Purpose: Centralize and validate application settings from multiple sources
- Location: `shared/config.py`
- Contains: Configuration dataclasses for Schoology, AWS, notifications, app settings, storage, logging
- Depends on: `dotenv` for environment loading, `tomllib`/`tomli` for TOML parsing
- Used by: All components via `get_config()` singleton

**Pipeline Orchestration Layer:**
- Purpose: Coordinate the complete grade monitoring workflow
- Location: `pipeline/orchestrator_v2.py`
- Contains: `GradePipelineV2` class orchestrating fetch → compare → notify → log steps
- Depends on: All other layers
- Used by: `main.py` entry point

## Data Flow

**Single Run Mode (main.py → GradePipelineV2.run_full_pipeline()):**

1. **Fetch** - `APIGradeFetcherV2.fetch_all_grades()` calls Schoology API via `SchoologyAPIClient`
   - Returns: `GradeData` model with all sections/periods/categories/assignments
2. **Compare** - `IDComparator.detect_changes(grade_data)` compares against `GradeStore` snapshots
   - Returns: `ChangeReport` with list of `GradeChange` objects
3. **Notify** - If `report.has_changes()`, `GradeNotifier` loads providers and sends via `NotificationManager`
   - Metadata enrichment by Gemini provider (AI analysis of grade changes)
   - Results aggregated across all providers
4. **Log** - `ChangeLogger.log_change_report()` writes JSON entry to `logs/grade_changes.log`
5. **Persist** - `GradeStore` updates all tables with new snapshot (ID-keyed for fast lookups)
6. **Health Check** - `_ping_healthcheck()` reports success/failure to healthchecks.io

**Daemon Mode (scheduler.py):**

1. Calculate next scheduled run time from `SCRAPE_TIMES` (e.g., "08:00,20:00")
2. Sleep until next time
3. Execute single run pipeline
4. Repeat

**State Management:**

- **Current State**: Stored in SQLite `data/grades.db` tables keyed by unique IDs from API
- **Change Detection**: Compares assignment IDs and grades; marks as new/updated/commented
- **Notification Trigger**: Only notify if changes exist (no "no changes" notifications)
- **Idempotency**: ID-based comparison prevents duplicate change notifications for unchanged grades

## Key Abstractions

**GradeData Model Hierarchy:**

```
GradeData (timestamp)
  └─ Section[] (section_id)
       └─ Period[] (period_id)
            └─ Category[] (category_id)
                 └─ Assignment[] (assignment_id)
                      ├─ earned_points, max_points
                      ├─ exception (Missing, Excused, Incomplete)
                      └─ comment
```

- Purpose: Represents complete grade snapshot with stable IDs at each level
- Examples: `shared/models.py` defines all four model classes
- Pattern: Pydantic BaseModel with decimal precision, date parsing validators

**Notification Message:**

- Purpose: Standardized format passed from pipeline to all notification providers
- Examples: `notifications/base.py` - `NotificationMessage` dataclass
- Pattern: Contains title, content, priority, optional URL, metadata dict for provider-specific data

**Change Report:**

- Purpose: Summary of all detected changes with categorization and human-readable formatting
- Examples: `shared/id_comparator.py` - `ChangeReport` dataclass
- Pattern: Tracks `new_assignments_count`, `grade_updates_count`, `comment_updates_count`; provides `.summary()` and `.format_for_notification()`

## Entry Points

**CLI Entry Point:**
- Location: `main.py`
- Triggers: User runs `python main.py [--daemon] [--times "HH:MM,HH:MM"]`
- Responsibilities: Parse arguments, setup logging, enter daemon loop or single run, handle signals

**Docker Entry Point:**
- Location: `scheduler.py` (called from `compose.yaml`)
- Triggers: Docker container start via `docker compose up`
- Responsibilities: Load config, calculate next run time, sleep and loop, spawn pipeline subprocesses

**Pipeline Entry Point:**
- Location: `pipeline/orchestrator_v2.py::GradePipelineV2.run_full_pipeline()`
- Triggers: Called from `main.py` or `scheduler.py`
- Responsibilities: Orchestrate complete workflow - fetch, compare, notify, log, save state, health check

## Error Handling

**Strategy:** Multi-level error recovery with graceful degradation

**Patterns:**

- **API Fetch Errors** (`_fetch_grades()` in orchestrator): Retries up to `max_retries` (default 3) with 5-second delays between attempts. Sends error notification on final failure.
- **Change Detection Errors** (`_detect_changes()` in orchestrator): Catches exceptions and returns empty `ChangeReport` with `is_initial=True`, allowing pipeline to continue without crashing.
- **Notification Errors** (`GradeNotifier`): Individual provider failures don't cascade; manager aggregates success across all providers and returns partial success.
- **Health Check Ping Errors** (`_ping_healthcheck()`): Caught and logged as warning; never fails the pipeline.
- **Configuration Errors** (`shared/config.py`): Raises `ValueError` if required API credentials missing; caught in `main.py` for graceful shutdown.

## Cross-Cutting Concerns

**Logging:**
- Framework: Python `logging` module
- Approach: Each module has `logger = logging.getLogger(__name__)`. Main entry configures handlers (stdout + file `logs/grade_scraper.log`). Daemon mode prefixes with "DAEMON". Debug logs in API client.

**Validation:**
- Pydantic models in `shared/models.py` validate all grade data; field validators parse decimals and dates
- Config validators in `shared/config.py` check required credentials via `get_config()` singleton
- Notification providers implement `is_available()` to check credentials before use

**Authentication:**
- OAuth 1.0a for Schoology API via `requests_oauthlib.OAuth1Session`
- Env vars for external service tokens: `PUSHOVER_TOKEN`, `GEMINI_KEY`, email credentials
- No inline credentials; all from `.env` file

**ID Preservation:**
- Core principle: Every model (`Assignment`, `Category`, `Period`, `Section`) has a stable `*_id` field from API
- Enables ID-based comparison in `IDComparator` instead of deep object diffing
- SQLite tables keyed by IDs for O(1) lookups during change detection

**Retry Logic:**
- API fetch retries with exponential backoff simulation (fixed 5-second delays)
- Notification delivery doesn't retry (one attempt per provider per run)
- Pipeline retries entire workflow on transient API failures, but doesn't retry on notification failures

---

*Architecture analysis: 2026-02-14*
