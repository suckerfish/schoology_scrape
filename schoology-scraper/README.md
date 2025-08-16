# Schoology Scraper

Independent grade scraping service for Schoology LMS.

## Overview

This service automatically scrapes student grades from Schoology, detects changes, and stores historical snapshots in AWS DynamoDB.

## Features

- **Web Scraping**: Uses Selenium WebDriver with Google OAuth authentication
- **Change Detection**: DeepDiff comparison to trigger notifications only on actual changes
- **Historical Storage**: AWS DynamoDB for timestamped grade snapshots
- **Notifications**: Pushover, email, and AI analysis via Google Gemini

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables** (create `.env` file):
   ```
   evan_google=your_google_email
   evan_google_pw=your_google_password
   aws_key=your_aws_access_key
   aws_secret=your_aws_secret_key
   pushover_token=your_pushover_token
   pushover_userkey=your_pushover_user_key
   gemini_key=your_gemini_api_key
   ```

3. **Run Scraper**:
   ```bash
   python run_scraper.py
   # or directly:
   python main.py
   ```

## Architecture

- `main.py` - Main orchestration script
- `driver_standard.py` - Selenium WebDriver implementation  
- `dynamodb_manager.py` - AWS DynamoDB interface
- `pushover.py`, `email_myself.py`, `gemini_client.py` - Notification providers
- `../shared/grade_data_service.py` - Shared data service interface

## Data Flow

1. **Login** → Schoology via Google OAuth
2. **Scrape** → Extract grade data from all courses
3. **Compare** → DeepDiff against previous snapshot
4. **Store** → Save to local JSON + DynamoDB  
5. **Notify** → Send alerts if changes detected

## Deployment

This package is designed to run independently as a scheduled service (cron job, Lambda, etc.) without requiring the dashboard component.