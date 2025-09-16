# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Schoology Grade Scraper** - an automated grade monitoring system that scrapes student grades from Schoology LMS, stores historical snapshots, and provides a comprehensive Streamlit dashboard for analysis.

## Architecture

The system follows a **Phase 3 modular pipeline architecture** with clean separation of concerns:

1. **Data Collection**: `pipeline/scraper.py` - Pure data extraction using standard Selenium WebDriver via Google OAuth
2. **Change Detection**: `pipeline/comparator.py` - DeepDiff-based change detection with fallback mechanisms
3. **Notifications**: `notifications/` - Plugin-based notification system with Pushover, Email, and AI analysis
4. **Orchestration**: `pipeline/orchestrator.py` - Main pipeline coordination with comprehensive error handling
5. **Storage**: `dynamodb_manager.py` - AWS DynamoDB for historical grade snapshots
6. **Dashboard**: `streamlit_viewer.py` + `pages/` - Multi-page interface for visualization and analysis

## Environment Setup

**Configuration System**: Uses hybrid TOML + .env approach for clean separation of settings vs secrets.

**Required files**:
- `config.toml` - Non-sensitive application settings (cache, retries, URLs, etc.)
- `.env` - Sensitive credentials only

**Required environment variables in `.env`**:
- `evan_google`/`evan_google_pw` - Google credentials for Schoology login
- `aws_key`/`aws_secret` - AWS DynamoDB credentials  
- `pushover_token`/`pushover_userkey` - Push notification credentials
- `gemini_key` - Google Gemini AI API key

**Application settings in `config.toml`**:
- App settings: log level, cache TTL, retry configuration
- Schoology settings: base URL
- AWS settings: region, DynamoDB table name
- Notification preferences: email enabled flag
- Logging settings: diff logging, retention periods

## Structured Diff Logging

The system provides comprehensive logging of grade changes for analysis and fine-tuning:

**Log Files:**
- `logs/grade_changes.log` - Structured JSON change tracking
- `logs/raw_diffs.log` - Debug-level DeepDiff output (configurable)

**Configuration in `config.toml`:**
```toml
[logging]
enable_change_logging = true          # Always enabled for production
enable_raw_diff_logging = false       # Debug only - can be large
change_log_retention_days = 90        # Historical change analysis
raw_diff_log_retention_days = 7       # Short-term troubleshooting
```

**Log Entry Structure:**
- Timestamp and change type classification
- Human-readable summary and formatted notification message
- Per-provider notification success/failure tracking
- Change metadata (grade changes, new assignments, removals)
- Comparison file references for audit trail
- Priority level for notification importance

**Benefits:**
- Analyze notification effectiveness and delivery patterns
- Fine-tune change detection and message formatting
- Debug notification failures with full context
- Track system reliability and performance over time
- Enable data-driven optimization of diff processing

## Common Commands

### Docker Deployment (Primary Method)
```bash
# Build and test
./docker-build.sh

# Run once
docker compose run --rm schoology-scraper

# Daily cron (production)
0 21 * * * cd /path/to/project && docker compose run --rm schoology-scraper
```

### Local Development (Legacy)
```bash
# Install dependencies (use uv for package management)
uv pip install -r requirements.txt

# Run main scraper
python main.py

# Launch Streamlit dashboard
streamlit run streamlit_viewer.py
```

### Data Structure

Grades are stored as nested dictionaries:
```
Course → Periods → Categories → Assignments
```

Each snapshot is timestamped and stored both locally (JSON) and in DynamoDB for historical tracking.

## Key Implementation Notes

- **Containerized Deployment**: Docker-first architecture with ARM64/x86_64 support using Chromium
- **Web Scraping**: Standard Selenium WebDriver with OAuth flow handling for Google authentication
- **Change Detection**: DeepDiff compares snapshots to trigger notifications only on actual changes
- **Plugin Architecture**: Notification providers use abstract interfaces for easy extensibility
- **Error Handling**: Comprehensive retry logic with exponential backoff and circuit breaker patterns
- **Dual Storage**: Local JSON files + AWS DynamoDB for redundancy and historical tracking
- **Multi-Modal UI**: Dashboard supports timeline navigation, filtering, and detailed assignment views
- **Structured Logging**: Comprehensive diff logging with JSON format for change analysis and notification tracking

## Streamlit Pages

- **Main**: Snapshot selector and hierarchical grade tree with change detection
- **Summary**: High-level metrics and missing assignments
- **Analytics**: Grade trends and statistical analysis with Plotly charts
- **Raw JSON**: Raw data inspection
- **Assignments**: Comprehensive assignment list with filtering and notes

## Optimization Guidelines

**IMPORTANT**: All optimizations and architectural changes require explicit user approval before implementation. Do not implement any optimization items autonomously, even if they appear in TODO lists or analysis. Always request specific permission for each optimization task before proceeding.

### Implementation Status
- ✅ **COMPLETED**: Full Phase 3 modular pipeline architecture
- ✅ **COMPLETED**: Docker containerization with ARM64 support
- ✅ **COMPLETED**: Plugin-based notifications (Pushover, Email, Gemini)
- ✅ **COMPLETED**: Dual storage (local JSON + DynamoDB)
- ✅ **COMPLETED**: Production deployment with cron scheduling

### Recent Improvements
- ✅ **ARM64 Compatibility**: Chromium-based browser stack for ARM64/x86_64 VPS deployment
- ✅ **Container Security**: Non-root execution with proper volume permissions
- ✅ **Automatic Scheduling**: Daily cron job setup for production monitoring
- ✅ **Error Recovery**: Robust driver detection and fallback mechanisms
- ✅ **Structured Diff Logging**: Comprehensive change tracking with JSON format for analysis and fine-tuning