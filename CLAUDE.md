# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Schoology Grade Scraper** - an automated grade monitoring system that scrapes student grades from Schoology LMS, stores historical snapshots, and provides a comprehensive Streamlit dashboard for analysis.

## Architecture

The system follows a layered architecture:

1. **Data Collection**: `driver_standard.py` uses standard Selenium WebDriver to scrape Schoology grades via Google OAuth
2. **Orchestration**: `main.py` coordinates scraping, change detection (DeepDiff), and notifications  
3. **Storage**: `dynamodb_manager.py` manages AWS DynamoDB for historical grade snapshots
4. **Notifications**: `pushover.py`, `email_myself.py`, `gemini_client.py` for alerts and AI analysis
5. **Dashboard**: `streamlit_viewer.py` + `pages/` multi-page interface for visualization and analysis

## Environment Setup

Required environment variables in `.env`:
- `evan_google`/`evan_google_pw` - Google credentials for Schoology login
- `aws_key`/`aws_secret` - AWS DynamoDB credentials  
- `pushover_token`/`pushover_userkey` - Push notification credentials
- `gemini_key` - Google Gemini AI API key

## Common Commands

### Development
```bash
# Install dependencies (use uv for package management)
uv pip install -r requirements.txt

# Run main scraper (typically scheduled)
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

- **Web Scraping**: Uses standard Selenium WebDriver with OAuth flow handling for Google authentication
- **Change Detection**: DeepDiff compares snapshots to trigger notifications only on actual changes
- **Hierarchical Data**: Complex nested structure requires careful parsing and display logic
- **Historical Tracking**: Immutable snapshots enable trend analysis and change attribution
- **Multi-Modal UI**: Dashboard supports timeline navigation, filtering, and detailed assignment views

## Streamlit Pages

- **Main**: Snapshot selector and hierarchical grade tree with change detection
- **Summary**: High-level metrics and missing assignments
- **Analytics**: Grade trends and statistical analysis with Plotly charts
- **Raw JSON**: Raw data inspection
- **Assignments**: Comprehensive assignment list with filtering and notes

## Optimization Guidelines

**IMPORTANT**: All optimizations and architectural changes require explicit user approval before implementation. Do not implement any optimization items autonomously, even if they appear in TODO lists or analysis. Always request specific permission for each optimization task before proceeding.

### Implementation Status
- ✅ **COMPLETED**: Migrated from undetected-chromedriver to standard Selenium WebDriver
  - `driver_standard.py` now used in production (includes OAuth account selection handling)
  - `driver.py` preserved as backup
  - Dependency on undetected-chromedriver can be removed from requirements.txt

### Known Optimization Opportunities  
- Add comprehensive caching to Streamlit pages
- Optimize DynamoDB queries to replace table scans
- Introduce service layer abstraction
- Centralize configuration management
- Add error handling and retry logic
- Separate data pipeline concerns