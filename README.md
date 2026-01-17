# Schoology Grade Scraper

Automated grade monitoring system that polls Schoology via API, detects changes using ID-based tracking, and sends notifications when grades are updated.

## What It Does

- **Automated Grade Tracking**: Fetches grades via Schoology REST API on a configurable schedule
- **ID-Based Change Detection**: Compares assignments by unique ID using SQLite for fast, reliable change detection
- **Smart Notifications**: Sends alerts via Pushover, email, and AI-generated summaries when grades change
- **Historical Tracking**: Stores grade state in SQLite database for trend analysis

## Key Features

### Efficient Monitoring
- **API-Based**: Direct REST API calls (~1 min per run vs 3+ min for browser automation)
- **ID-Based Comparison**: Fast O(1) lookups by assignment ID, no false positives from formatting differences
- **Flexible Scheduling**: Configure exact run times (e.g., "08:00,20:00" for 8am and 8pm daily)

### Multi-Channel Notifications
- **Pushover**: Instant mobile notifications
- **Email**: Detailed grade reports
- **AI Analysis**: Gemini AI provides natural language summaries
- **JSON Logging**: Structured change logs in `logs/grade_changes.log`

### Robust Architecture
- **SQLite State Tracking**: Persistent storage in `data/grades.db`
- **Plugin-Based Notifications**: Easy to add new providers
- **Comprehensive Error Handling**: Retry logic and graceful failure recovery
- **Docker Deployment**: Containerized with ARM64/x86_64 support

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Schoology API credentials (from school admin)
- AWS account for DynamoDB (optional)

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd schoology_scrape
   ```

2. **Configure environment variables** in `.env`:
   ```bash
   # Schoology API credentials (required)
   SCHOOLOGY_API_KEY=your-api-key
   SCHOOLOGY_API_SECRET=your-api-secret
   SCHOOLOGY_DOMAIN=yourdomain.schoology.com

   # Scheduling (optional, defaults to 8am/8pm)
   SCRAPE_TIMES=08:00,20:00

   # AWS DynamoDB (optional)
   aws_key=your-aws-access-key
   aws_secret=your-aws-secret-key

   # Notifications (optional)
   pushover_token=your-pushover-app-token
   pushover_userkey=your-pushover-user-key
   gemini_key=your-google-gemini-api-key
   ```

3. **Deploy with Docker**:
   ```bash
   docker compose up -d      # Start monitoring
   docker compose logs -f    # View logs
   docker compose down       # Stop
   ```

## Configuration

### Scheduling
Set `SCRAPE_TIMES` environment variable with 24-hour format times:
```bash
SCRAPE_TIMES=08:00,20:00       # Twice daily
SCRAPE_TIMES=21:00             # Once daily at 9 PM
SCRAPE_TIMES=07:00,13:00,19:00 # Three times daily
```

### Application Settings
Modify `config.toml` for:
- Retry logic and timeouts
- AWS DynamoDB configuration
- Logging preferences and retention
- Notification provider settings

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
- **`data/grades.db`**: Current grade state with full history
- Fast ID-based lookups for change detection
- See `ID_BASED_SYSTEM.md` for schema details

### Logs
- **`logs/grade_changes.log`**: JSON-formatted change history
- **`grade_scraper.log`**: Application logs

### AWS DynamoDB (Optional)
- Historical snapshots for cross-device access
- Configurable via `config.toml`

## Architecture

### Core Components
- **API Fetcher** (`api/fetch_grades_v2.py`): Schoology REST API client
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

## Development

### Local Development
```bash
# Install dependencies
uv pip install -r requirements.txt

# Run single scrape
python main.py

# Run tests
python -m pytest tests/test_id_comparator.py -v
```

### Testing
```bash
# Unit tests (8 tests)
python -m pytest tests/test_id_comparator.py -v

# Integration test
python test_new_system.py
```

## Troubleshooting

### Common Issues

- **401 Unauthorized**: Check `SCHOOLOGY_API_KEY` and `SCHOOLOGY_API_SECRET` in `.env`
- **403 Forbidden on assignments**: Some assignments have permission restrictions (normal)
- **Section ID mismatch warnings**: Handled automatically with fuzzy matching

### Database Reset
```bash
rm data/grades.db  # Next run recreates database
```

### Monitoring
```bash
docker compose ps              # Container status
docker compose logs -f         # Real-time logs
sqlite3 data/grades.db ".tables"  # Check database
```

## License

This project is for educational purposes. Please ensure compliance with your institution's terms of service.
