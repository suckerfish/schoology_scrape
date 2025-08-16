# Schoology Dashboard

Independent Streamlit dashboard for visualizing Schoology grade data.

## Overview

Multi-page web interface for analyzing grade trends, comparing snapshots, and tracking assignment progress.

## Features

- **Grade Tree View**: Hierarchical display of courses → periods → categories → assignments
- **Change Detection**: Compare any two snapshots to see what changed
- **Analytics**: Grade trends and statistical analysis with Plotly charts
- **Assignment Tracking**: Comprehensive assignment list with filtering and notes
- **Historical Navigation**: Timeline selector for any stored snapshot

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables** (create `.env` file):
   ```
   aws_key=your_aws_access_key
   aws_secret=your_aws_secret_key
   ```

3. **Run Dashboard**:
   ```bash
   python run_dashboard.py
   # or directly:
   streamlit run streamlit_viewer.py
   ```

## Pages

- **Main** (`streamlit_viewer.py`): Snapshot selector and hierarchical grade tree
- **Summary** (`pages/01_Summary.py`): High-level metrics and missing assignments
- **Analytics** (`pages/02_Analytics.py`): Grade trends and statistical charts
- **Raw JSON** (`pages/03_Raw_JSON.py`): Raw data inspection
- **Assignments** (`pages/04_Assignments.py`): Comprehensive assignment list

## Architecture

- Uses shared data service (`../shared/grade_data_service.py`)
- Connects to same DynamoDB table as scraper
- Independent deployment - no scraper dependencies
- Streamlit multi-page application

## Data Access

The dashboard reads grade snapshots from AWS DynamoDB using the shared `GradeDataService` interface. It doesn't require the scraper to be running and can operate independently.

## Deployment

This package can be deployed as:
- Local Streamlit app (`streamlit run streamlit_viewer.py`)
- Containerized web service  
- Cloud hosting (Streamlit Cloud, Heroku, etc.)

The dashboard is read-only and doesn't perform any scraping operations.