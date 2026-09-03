# Schoology Grade Scraper

Automated grade monitoring system that polls Schoology via API, detects changes using ID-based tracking, and emails you when grades are updated.

## What It Does

- **Automated Grade Tracking**: Fetches grades via the Schoology REST API on a configurable schedule
- **ID-Based Change Detection**: Compares assignments by unique ID using SQLite for fast, reliable change detection
- **Notifications**: Emails a structured grade report, optionally with a Gemini AI summary
- **Historical Tracking**: Stores grade state in SQLite and a JSON change log

Notifications are sent **only when grades actually change**. Uptime is confirmed separately through healthchecks.io.

## Key Features

### Efficient Monitoring
- **API-Based**: Direct REST API calls; a run takes roughly 10 seconds
- **ID-Based Comparison**: O(1) lookups by assignment ID, no false positives from formatting differences
- **Flexible Scheduling**: Configure exact run times (e.g., "08:00,20:00" for 8am and 8pm daily)

### Notifications
- **Email**: Styled HTML report grouped by course, period, and category
- **AI Analysis**: Gemini generates a natural-language summary appended to the email
- **JSON Logging**: Structured change history in `logs/grade_changes.log`

### Architecture
- **SQLite State Tracking**: Persistent storage in `data/grades.db`, pruned automatically
- **Plugin-Based Notifications**: Providers load only when their credentials are present
- **Docker Deployment**: Multi-arch image (amd64 + arm64) published to GHCR

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Schoology API credentials (from your Schoology account settings)

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/suckerfish/schoology_scrape
   cd schoology_scrape
   ```

2. **Configure environment variables** in `.env` (see `.env.example`):
   ```bash
   # Schoology API credentials (required)
   SCHOOLOGY_API_KEY=your-api-key
   SCHOOLOGY_API_SECRET=your-api-secret

   # Scheduling (optional, defaults to 21:00)
   SCRAPE_TIMES=08:00,20:00

   # Email notifications (optional)
   email_sender=your-sender-email@gmail.com
   email_password=your-gmail-app-password
   email_receiver=recipient@example.com

   # AI summaries (optional)
   gemini_key=your-google-gemini-api-key

   # Uptime monitoring (optional, recommended)
   HEALTHCHECKS_URL=https://hc-ping.com/your-uuid-here
   ```

3. **Deploy with Docker**:
   ```bash
   docker compose up -d      # Start monitoring
   docker compose logs -f    # View logs
   docker compose down       # Stop
   ```

`compose.yaml` pulls `ghcr.io/suckerfish/schoology_scrape:latest`, built by GitHub Actions on every push to `main`.

## Configuration

### Scheduling
Set the `SCRAPE_TIMES` environment variable with 24-hour times:
```bash
SCRAPE_TIMES=08:00,20:00       # Twice daily
SCRAPE_TIMES=21:00             # Once daily at 9 PM
SCRAPE_TIMES=07:00,13:00,19:00 # Three times daily
```

### Application Settings
`config.toml` holds non-sensitive settings:
- `log_level`, `max_retries`, `data_directory`
- Change-log retention (`change_log_retention_days`)
- `email_enabled`

Credentials always come from `.env`, never from `config.toml`.

## Data Structure

Grades are organized hierarchically:
```
Course → Periods → Categories → Assignments
```

Each assignment contains:
- **Assignment ID**: Unique identifier from Schoology
- **Grade**: Points earned/max (e.g., "88/100")
- **Exception**: Missing, Excused, or Incomplete status
- **Comment**: Teacher feedback
- **Due Date**: Assignment deadline

## Storage

### SQLite Database
- **`data/grades.db`**: Current grade state
- Sections that stop appearing in the API feed are pruned automatically, along with their periods, categories, and assignments

### Logs
- **`logs/grade_changes.log`**: JSON change history, trimmed to the retention window
- **`logs/grade_scraper.log`**: Application log, rotated at 5 MB

## Architecture

### Core Components
- **API Client** (`api/client.py`): OAuth 1.0a Schoology REST client
- **API Fetcher** (`api/fetch_grades_v2.py`): Builds `GradeData` models from the API
- **ID Comparator** (`shared/id_comparator.py`): Change detection by assignment ID
- **Grade Store** (`shared/grade_store.py`): SQLite state management
- **Notifications** (`notifications/`): Plugin-based alert system
- **Orchestrator** (`pipeline/orchestrator_v2.py`): Pipeline coordination

### Data Flow
```
Schoology API → APIGradeFetcherV2 → GradeData (Pydantic models)
                                          ↓
                                   IDComparator
                                          ↓
                                   GradeStore (SQLite)
                                          ↓
                                   ChangeReport → Notifications
```

### Section ID Matching

Schoology can report the same course under two different section IDs: one in the
grades feed and another in the user's sections list. Detail endpoints
(assignments, grading categories) are usually authorized on only one of them.
The fetcher resolves this by looking the section up directly and joining the two
IDs on `course_id`, then tries both IDs for every detail request.

## Development

### Local Development
```bash
# Install dependencies
uv pip install -r requirements.txt

# Run a single scrape
python main.py

# Run in daemon mode
python main.py --daemon --times "08:00,20:00"

# Run tests
python -m pytest tests/ -v
```

## Troubleshooting

### Common Issues

- **401 Unauthorized**: Check `SCHOOLOGY_API_KEY` and `SCHOOLOGY_API_SECRET` in `.env`
- **403 Forbidden**: Some sections deny detail endpoints on one of their two IDs; the fetcher retries with the other
- **"Unknown Course" in a notification**: The section could not be resolved by ID or `course_id`. Check the fetch warnings in the log.

### Database Reset
```bash
rm data/grades.db  # Next run recreates it and treats the result as an initial capture
```

### Monitoring
```bash
docker compose ps                 # Container status
docker compose logs -f            # Real-time logs
sqlite3 data/grades.db ".tables"  # Check database
```

### Uptime Monitoring (Healthchecks.io)

The scraper pings healthchecks.io on each run. If pings stop, you get alerted.

1. Create a free account at [healthchecks.io](https://healthchecks.io)
2. Create a check with a period matching your `SCRAPE_TIMES` interval
3. Add the ping URL to `.env`: `HEALTHCHECKS_URL=https://hc-ping.com/your-uuid`

Because notifications only fire when grades change, healthchecks.io is what confirms the scraper is still running on quiet days.

## License

This project is for educational purposes. Please ensure compliance with your institution's terms of service.
