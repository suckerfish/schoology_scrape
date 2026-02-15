# Codebase Structure

**Analysis Date:** 2026-02-14

## Directory Layout

```
schoology_scrape/
├── main.py                 # CLI entry point (single-run or daemon mode)
├── scheduler.py            # Scheduler for Docker container
├── compose.yaml            # Docker Compose configuration
├── config.toml             # Application settings (retries, logging, schedule)
├── Dockerfile              # Docker image definition
├── entrypoint.sh           # Docker entrypoint script
├── requirements.txt        # Python package dependencies
│
├── api/                    # Schoology API client and data fetching
│   ├── __init__.py
│   ├── client.py          # OAuth 1.0a API client (low-level HTTP)
│   ├── fetch_grades_v2.py # Grade fetcher building GradeData models
│   └── fetch_grades.py    # Legacy implementation (not actively used)
│
├── pipeline/              # Pipeline orchestration and notifications
│   ├── __init__.py
│   ├── orchestrator_v2.py # Main pipeline coordinator
│   ├── notifier.py        # Notification delivery wrapper
│   ├── error_handling.py  # Error recovery utilities
│   └── api_scraper.py     # Legacy scraper (not actively used)
│
├── notifications/         # Plugin-based notification system
│   ├── __init__.py
│   ├── base.py           # Abstract base class and message format
│   ├── manager.py        # Provider manager and loader
│   ├── pushover_provider.py   # Pushover mobile notifications
│   ├── email_provider.py      # SMTP email notifications
│   └── gemini_provider.py     # Google Generative AI analysis
│
├── shared/               # Core shared modules (models, comparison, storage)
│   ├── __init__.py
│   ├── models.py         # Pydantic models (Assignment, Category, Period, Section, GradeData)
│   ├── config.py         # Configuration management and validation
│   ├── grade_store.py    # SQLite database layer for grade snapshots
│   ├── id_comparator.py  # ID-based change detection (GradeChange, ChangeReport)
│   └── change_logger.py  # JSON change history logger
│
├── tests/                # Test suite
│   ├── test_id_comparator.py      # Tests for change detection
│   ├── test_grade_store.py        # Tests for SQLite storage
│   ├── test_fetch_grades.py       # Tests for API fetching
│   ├── test_notifications.py      # Tests for notification providers
│   ├── test_real_comparison.py    # Integration tests
│   ├── simple_test.py             # Basic smoke tests
│   └── debug_*.py                 # Development/debugging utilities
│
├── dev_tools/            # Development utilities (not part of main app)
│   └── api/              # Debugging scripts for API issues
│
├── data/                 # SQLite database and snapshots
│   ├── grades.db        # Main state storage (created at runtime)
│   └── *.json           # Legacy snapshot files (not used in ID-based system)
│
├── logs/                 # Log files (created at runtime)
│   ├── grade_scraper.log     # Main application log
│   ├── grade_changes.log     # JSON change history
│   └── scheduler.log         # Scheduler log (Docker mode)
│
├── .env.example          # Environment variable template
├── .gitignore           # Git exclusions (*.db, .env, __pycache__)
├── README.md            # Project documentation
└── ID_BASED_SYSTEM.md   # Technical documentation of ID-based change detection
```

## Directory Purposes

**api/**
- Purpose: Schoology API client and data fetching logic
- Contains: OAuth 1.0a HTTP client, grade fetcher with model building
- Key files: `client.py`, `fetch_grades_v2.py`

**pipeline/**
- Purpose: Orchestrate the complete grade monitoring workflow
- Contains: Main orchestrator, notification coordination, error handling
- Key files: `orchestrator_v2.py` (core logic)

**notifications/**
- Purpose: Plugin architecture for sending alerts via multiple channels
- Contains: Abstract base class, provider implementations, notification manager
- Key files: `base.py` (interfaces), `manager.py` (loader), provider files (implementation)

**shared/**
- Purpose: Core domain models, configuration, data storage, and change detection
- Contains: Pydantic models, SQLite database layer, ID-based comparator, JSON logger
- Key files: `models.py`, `grade_store.py`, `id_comparator.py`, `config.py`

**tests/**
- Purpose: Unit and integration tests for all components
- Contains: pytest test files, test fixtures, debug utilities
- Key files: Named `test_*.py`; organized by tested component

**data/**
- Purpose: Runtime data storage
- Contains: SQLite database (`grades.db`) created on first run
- Generated: Yes; created by `GradeStore._init_db()`
- Committed: No; in `.gitignore`

**logs/**
- Purpose: Application and change history logs
- Contains: Main app log, JSON change log, scheduler log
- Generated: Yes; created by logging setup in `main.py` and `scheduler.py`
- Committed: No; in `.gitignore`

## Key File Locations

**Entry Points:**
- `main.py`: User-facing CLI entry point; supports single-run and daemon modes
- `scheduler.py`: Scheduler for Docker container; sleeps between runs
- `pipeline/orchestrator_v2.py`: Core pipeline logic; executed by both entry points

**Configuration:**
- `.env`: Environment variables (API keys, service tokens) - **not committed**
- `.env.example`: Template showing required variables
- `config.toml`: Application settings (retries, logging, schedule) - **committed**

**Core Logic:**
- `api/fetch_grades_v2.py`: Fetches grades from API, builds `GradeData` models
- `shared/id_comparator.py`: Detects changes by comparing assignment IDs
- `shared/grade_store.py`: SQLite storage for snapshots
- `notifications/manager.py`: Loads and dispatches notifications

**Testing:**
- `tests/test_id_comparator.py`: Core change detection tests
- `tests/test_grade_store.py`: Database layer tests
- `tests/test_fetch_grades.py`: API fetching tests
- `tests/test_notifications.py`: Notification provider tests

## Naming Conventions

**Files:**
- `*.py`: Python source files
- `*_v2.py`: Indicates second version (e.g., `fetch_grades_v2.py`, `orchestrator_v2.py`)
- `test_*.py`: pytest test files
- `debug_*.py`: Development/debugging utilities (not part of main app)
- `*_provider.py`: Notification provider implementations

**Directories:**
- Lowercase plural nouns: `api/`, `notifications/`, `shared/`, `tests/`, `dev_tools/`, `logs/`, `data/`
- All user-facing paths follow this convention

**Modules:**
- CamelCase for classes: `GradePipelineV2`, `IDComparator`, `GradeStore`, `NotificationProvider`
- snake_case for functions and variables: `fetch_all_grades()`, `detect_changes()`, `run_full_pipeline()`
- UPPER_CASE for constants: `BASE_URL` in `SchoologyAPIClient`

**Database Tables:**
- Lowercase with underscores: `snapshots`, `sections`, `periods`, `categories`, `assignments`
- ID columns: `section_id`, `period_id`, `category_id`, `assignment_id` (primary keys)
- Timestamps: `last_updated`, `created_at` (ISO format strings)

## Where to Add New Code

**New Feature (e.g., SMS notifications):**
- Primary code: `notifications/sms_provider.py` (implement `NotificationProvider` abstract class)
- Configuration: Add config field to `NotificationConfig` in `shared/config.py`
- Manager update: `notifications/manager.py` auto-loads providers if `is_available()` returns True
- Tests: `tests/test_notifications.py` add new provider test case

**New Component/Module (e.g., Grade analysis service):**
- Implementation: Create in `shared/` if shared utility, or `pipeline/` if orchestration-related
- Models: Add to `shared/models.py` if new data structure needed
- Tests: Create `tests/test_[component].py` following existing test patterns
- Configuration: Add to appropriate dataclass in `shared/config.py`

**Utilities/Helpers:**
- Shared helpers: `shared/` directory (e.g., new comparator strategy in `id_comparator.py`)
- API utilities: `api/` directory (e.g., new API client method in `client.py`)
- Pipeline utilities: `pipeline/` directory (e.g., new error handling strategy in `error_handling.py`)

**Tests:**
- Always in `tests/` directory (not co-located with source)
- Named `test_*.py` or `debug_*.py`
- Use pytest fixtures for setup/teardown (see `test_id_comparator.py::temp_db` fixture)
- Use temporary files for database tests (see `tempfile.NamedTemporaryFile()` pattern)

## Special Directories

**dev_tools/**
- Purpose: Development-only utilities; excluded from main app logic
- Generated: No
- Committed: Yes
- Used for: Debugging specific API issues or data analysis

**.planning/codebase/**
- Purpose: GSD mapping documents (this file and related docs)
- Generated: Yes (by GSD mapper)
- Committed: Yes
- Used for: Orchestrator context when planning new phases

## Import Patterns

**Relative imports within modules:**
- From `api/`: Use absolute imports: `from shared.models import GradeData`
- From `pipeline/`: Use absolute imports: `from shared.grade_store import GradeStore`
- From `notifications/`: Use absolute imports: `from shared.config import get_config`

**Top-level imports in entry points:**
- Prefer absolute: `from pipeline.orchestrator_v2 import GradePipelineV2`
- Avoid relative imports in `main.py` and `scheduler.py`

**Pydantic models:**
- All imported from `shared.models`: `from shared.models import Assignment, Category, Period, Section, GradeData`

**Configuration:**
- Always use `from shared.config import get_config` and call `get_config()` to retrieve singleton

## Module Responsibilities

**api/client.py:**
- Low-level HTTP communication with Schoology API
- OAuth 1.0a authentication
- Responsibility: GET requests, error handling, user ID caching

**api/fetch_grades_v2.py:**
- High-level grade data fetching
- Transforms API responses into `GradeData` models
- Responsibility: API orchestration, model building, ID preservation

**shared/models.py:**
- Data structure definitions
- Pydantic validation
- Responsibility: Type safety, field parsing (decimals, dates, enums)

**shared/grade_store.py:**
- SQLite database operations
- State persistence
- Responsibility: CRUD for grade snapshots, ID-based lookups

**shared/id_comparator.py:**
- Change detection logic
- Comparison using unique IDs
- Responsibility: Detect new/updated/commented assignments, aggregate into `ChangeReport`

**shared/change_logger.py:**
- JSON logging of changes
- Responsibility: Write structured history, cleanup old logs

**shared/config.py:**
- Configuration loading from multiple sources
- Dataclass definitions for all config sections
- Responsibility: Load `.env` and `config.toml`, singleton pattern

**notifications/base.py:**
- Abstract base class for providers
- Message format definition
- Responsibility: Define provider interface

**notifications/manager.py:**
- Provider discovery and instantiation
- Notification dispatch
- Responsibility: Load available providers, aggregate results

**notifications/*_provider.py:**
- Concrete provider implementations
- Responsibility: Send to specific service (Pushover, Email, Gemini)

**pipeline/orchestrator_v2.py:**
- Main pipeline workflow
- Responsibility: Coordinate fetch → compare → notify → log → save

**pipeline/notifier.py:**
- Notification delivery coordination
- Responsibility: Adapt `ChangeReport` to notification format, handle errors

**main.py:**
- CLI argument parsing
- Logging setup
- Responsibility: Entry point, daemon/single-run mode switching

**scheduler.py:**
- Docker container scheduler
- Responsibility: Calculate next run time, sleep loop, subprocess spawning

---

*Structure analysis: 2026-02-14*
