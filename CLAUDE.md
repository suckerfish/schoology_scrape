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
- **Plugin Architecture**: Notification providers use abstract interfaces for easy extensibility
- **Error Handling**: Comprehensive retry logic with exponential backoff and circuit breaker patterns
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
- ✅ **COMPLETED Phase 1**: Decoupled Streamlit viewer from scraper components
- ✅ **COMPLETED Phase 2**: Service layer abstraction and centralized configuration management  
- ✅ **COMPLETED Phase 3**: Pipeline refactoring with plugin-based notifications and error handling
- ✅ **COMPLETED Conditional Storage**: Restored logic to only save data when changes are detected

### Architecture Evolution
- ✅ **Plugin-Based Notifications**: `notifications/` directory with abstract providers (Pushover, Email, Gemini)
- ✅ **Separated Pipeline**: `pipeline/` directory with focused components (scraper, comparator, notifier, orchestrator)
- ✅ **Error Handling**: Comprehensive retry logic, circuit breakers, and severity-based error tracking
- ✅ **Configuration Management**: Hybrid TOML + .env approach with structured dataclasses
- ✅ **Testing Framework**: `test_pipeline.py` validates all components end-to-end
- ✅ **Conditional Storage**: Enhanced orchestrator with configurable storage behavior (`config.toml` storage section)

### Legacy Cleanup Opportunities  
- Remove `undetected-chromedriver==3.5.4` from requirements.txt (no longer used)
- Archive old backup files after successful Phase 3 operation