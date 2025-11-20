# Schoology Grade Scraper

An automated grade monitoring system that scrapes student grades from Schoology LMS, tracks changes over time, and provides intelligent notifications when grades are updated.

> **Recommended Branch**: Use `docker-containerization` branch for the latest stable deployment with Docker support.

## What It Does

- **Automated Grade Tracking**: Logs into Schoology via Google OAuth and extracts all course grades and assignments
- **Change Detection**: Compares current grades with historical snapshots to detect new grades, assignment additions, and due date changes
- **Smart Notifications**: Sends alerts via Pushover, email, and AI-generated summaries when changes are detected
- **Historical Analysis**: Stores grade data locally and in AWS DynamoDB for trend analysis and reporting

## Key Features

### Intelligent Monitoring
- **Flexible Scheduling**: Configure exact run times (e.g., "8:00,20:00" for 8am and 8pm daily)
- **Change Detection**: Uses DeepDiff to identify exactly what changed between grade snapshots
- **Priority-Based Alerts**: Distinguishes between actual grade changes and administrative updates

### Multi-Channel Notifications
- **Pushover**: Instant mobile notifications for grade changes
- **Email**: Detailed grade reports sent to configured recipients
- **AI Analysis**: Gemini AI provides natural language summaries of changes
- **Structured Logging**: JSON-formatted change logs for analysis and debugging

### Robust Architecture
- **Plugin-Based Notifications**: Easy to add new notification providers
- **Dual Storage**: Local JSON files + AWS DynamoDB for redundancy
- **Comprehensive Error Handling**: Retry logic, circuit breakers, and graceful failure recovery
- **Docker Deployment**: Containerized with ARM64/x86_64 support for VPS deployment

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Google account with Schoology access
- AWS account for DynamoDB (optional but recommended)

### Setup
1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd schoology_scrape
   git checkout docker-containerization
   ```

2. **Configure environment variables** in `.env`:
   ```bash
   # Schoology credentials
   evan_google=your-email@domain.com
   evan_google_pw=your-password

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
   # Build and start continuous monitoring
   docker compose up -d

   # View logs
   docker compose logs -f

   # Manual single run
   docker compose run --rm --profile manual schoology-scraper
   ```

## Configuration

### Scheduling
Set `SCRAPE_TIMES` environment variable with 24-hour format times:
```bash
SCRAPE_TIMES=08:00,20:00      # Twice daily
SCRAPE_TIMES=21:00            # Once daily at 9 PM
SCRAPE_TIMES=07:00,13:00,19:00 # Three times daily
```

### Application Settings
Modify `config.toml` for:
- Cache settings and retry logic
- AWS DynamoDB configuration
- Logging preferences and retention
- Notification provider settings

## Data Structure

Grades are organized hierarchically:
```
Course → Periods → Categories → Assignments
```

Each assignment contains:
- **Grade**: Current score (e.g., "88/100", "A-", "Not graded")
- **Due Date**: Assignment deadline
- **Comments**: Teacher feedback
- **Title**: Assignment name

## Storage and Logging

### Local Files
- **`data/all_courses_data_YYYYMMDD_HHMMSS.json`**: Daily grade snapshots
- **`logs/grade_changes.log`**: Structured change detection logs
- **`logs/raw_diffs.log`**: Debug-level diff data (optional)

### AWS DynamoDB
- Historical grade snapshots stored with timestamps
- Provides redundancy and enables cross-device access
- Configurable via `config.toml`

### Log Analysis
Change logs include:
- Change summaries and detailed breakdowns
- Notification delivery status per provider
- Change classification (grade changes vs. administrative updates)
- Priority levels for filtering important changes

## Notification Examples

### Grade Change Alert
```
Changes detected: 1 value(s) changed

Detailed changes:
• Math 7 test grade: 85/100 → 88/100, period grade now 91%

--- AI Analysis ---
Math test grade improved from 85/100 to 88/100, boosting the overall period grade to 91%.
```

### New Assignment Alert
```
Changes detected: 1 list item(s) added

--- AI Analysis ---
'Bill Nye Atoms' assignment added to Science 7 (due 9/19/25 3:59pm, ungraded)
```

## Architecture

### Core Components
- **Scraper** (`pipeline/scraper.py`): Selenium-based data extraction
- **Comparator** (`pipeline/comparator.py`): DeepDiff change detection
- **Notifications** (`notifications/`): Plugin-based alert system
- **Storage** (`dynamodb_manager.py`): Dual local/cloud persistence

### Error Handling
- **Retry Logic**: Exponential backoff for transient failures
- **Circuit Breakers**: Protect against cascading failures
- **Graceful Degradation**: Continue operation if individual components fail
- **Comprehensive Logging**: Track errors and system health

## Development

### Local Development
```bash
# Install dependencies
uv pip install -r requirements.txt

# Run single scrape
python main.py

# Test components
python test_pipeline.py
```

### Adding Notification Providers
Extend the `NotificationProvider` base class in `notifications/base.py`:

```python
class CustomProvider(NotificationProvider):
    @property
    def provider_name(self) -> str:
        return "custom"

    def send(self, message: NotificationMessage) -> bool:
        # Implementation
        pass
```

## Troubleshooting

### Common Issues
- **Authentication**: Verify Google credentials in `.env`
- **Permissions**: Check Docker volume permissions for data directory
- **Scheduling**: Ensure `SCRAPE_TIMES` format is correct (24-hour, comma-separated)
- **Dependencies**: Use `docker-containerization` branch for latest fixes

### Monitoring
```bash
# Check container status
docker compose ps

# View real-time logs
docker compose logs -f

# Debug scheduling
docker compose exec schoology-scraper env | grep SCRAPE_TIMES
```

## License

This project is for educational purposes. Please ensure compliance with your institution's terms of service when using automated tools to access their systems.