# API Polling Branch - README

**Branch:** `api-polling`
**Status:** ⚠️ Experimental - Has known formatting issues
**Created:** 2025-09-30

## Overview

Alternative implementation that uses the Schoology REST API instead of Selenium web scraping for grade data collection. Significantly faster and more reliable than browser automation.

## Key Differences from docker-containerization

| Feature | docker-containerization (Scraper) | api-polling (API) |
|---------|-----------------------------------|-------------------|
| **Data Source** | Selenium + Chromium browser | Schoology REST API |
| **Authentication** | Google OAuth via browser | OAuth 1.0a API credentials |
| **Speed** | ~2-3 minutes | ~30 seconds |
| **Reliability** | Brittle (UI changes break it) | Stable (API contract) |
| **Docker Image** | ~500MB | ~1.1GB* |
| **Dependencies** | selenium, chromium, xvfb | requests-oauthlib only |
| **Data Coverage** | 100% including comments | 97.5% (78/80 assignments) |
| **Teacher Comments** | ✅ Full access | ⚠️ Limited/unavailable |

*Still large due to pandas/numpy/streamlit for dashboard, not the API client itself

## Prerequisites

### 1. Obtain Schoology API Credentials

You need API credentials from Schoology:

1. Log into Schoology as an admin or request credentials from your district
2. Navigate to: **Tools → School Management → API**
3. Create a new application and note:
   - **Consumer Key** (API Key)
   - **Consumer Secret** (API Secret)

### 2. Update .env File

```bash
# Schoology API Credentials (required for api-polling branch)
SCHOOLOGY_API_KEY=your-api-key-here
SCHOOLOGY_API_SECRET=your-api-secret-here
SCHOOLOGY_DOMAIN=yourdomain.schoology.com

# Keep existing notification and storage credentials
SCRAPE_TIMES=08:00,20:00
aws_key=your-aws-key
aws_secret=your-aws-secret
pushover_token=your-pushover-token
pushover_userkey=your-pushover-userkey
gemini_key=your-gemini-key
```

**Note:** You do NOT need `evan_google` or `evan_google_pw` credentials on this branch.

## Architecture Changes

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ docker-containerization (Selenium)                          │
├─────────────────────────────────────────────────────────────┤
│ pipeline/scraper.py (Selenium)                              │
│   → Login via Google OAuth                                  │
│   → Navigate Schoology UI                                   │
│   → Extract HTML elements                                   │
│   → Return structured JSON                                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ api-polling (REST API)                                      │
├─────────────────────────────────────────────────────────────┤
│ pipeline/api_scraper.py                                     │
│   → api/client.py (OAuth 1.0a)                             │
│   → api/fetch_grades.py                                     │
│   → REST API calls                                          │
│   → Return structured JSON                                  │
└─────────────────────────────────────────────────────────────┘

Both converge at:
  → pipeline/comparator.py
  → notifications/
  → dynamodb_manager.py
```

### New Files in api-polling Branch

- `api/client.py` - Schoology API OAuth 1.0a client
- `api/fetch_grades.py` - Grade data fetcher matching scraper output format
- `pipeline/api_scraper.py` - Drop-in replacement for `pipeline/scraper.py`

### Modified Files

- `pipeline/orchestrator.py` - Uses `APIGradeScraper` instead of `GradeScraper`
- `main.py` - Updated log message to "API Polling Mode"
- `requirements.txt` - Removed selenium/beautifulsoup, added requests-oauthlib
- `Dockerfile` - Removed Chromium/browser dependencies
- `.env.example` - Added API credential examples

## Usage

### Docker (Recommended)

```bash
# Switch to api-polling branch
git checkout api-polling

# Build image (first time or after changes)
docker compose build

# Run once manually to test
docker compose run --rm schoology-scheduler python -u main.py

# Deploy as scheduled service
docker compose up -d

# View logs
docker compose logs -f schoology-scheduler

# Stop
docker compose down
```

### Local Development

```bash
# Switch to branch
git checkout api-polling

# Install dependencies
uv pip install -r requirements.txt

# Run once
python main.py

# View dashboard
streamlit run streamlit_viewer.py
```

## Known Issues

### ⚠️ Critical: Format Mismatches Causing False Positives

**Status:** Documented in `TODO_API_FORMATTING.md`

The API output format differs slightly from the scraper output, causing the diff detector to flag changes when nothing actually changed:

1. **Grade Format**
   - Scraper: `"10 / 10 / 10"` (3 numbers)
   - API: `"10 / 10"` (2 numbers)

2. **Date Format**
   - Scraper: `"8/20/25 3:59pm"` (no leading zeros)
   - API: `"08/20/25 03:59pm"` (leading zeros)

3. **Category Names**
   - Scraper: `"Class Projects (30%)"` (consistent weights)
   - API: Sometimes includes weights, sometimes doesn't

**Impact:** Current implementation sends notifications with 100+ "changes" even when nothing real changed.

**Workaround:** Ignore first notification after switching to this branch. Subsequent notifications will only show deltas from the last API fetch (still may have formatting noise).

**Fix:** See `TODO_API_FORMATTING.md` for implementation steps.

### Missing Data

**Assignments not in API (2/80):**
- "Diffusion Lab DB" (Science)
- "warm up 8.21.25" (Science)

**403 Permission Errors (3 assignments):**
Some assignments return 403 Forbidden when fetching details. These show as "Assignment XXXXXXX" without proper titles.

**Teacher Comments:**
API returns very few teacher grade comments compared to scraper. If comments are critical for your notifications, stay on docker-containerization branch.

## API Investigation Files

The `api/` directory contains additional tools from the API investigation:

- `compare_data.py` - Compare API vs scraper output
- `analyze_mismatches.py` - Deep dive analysis of differences
- `test_api.py` - Quick API connectivity test
- `COMPARISON_FINDINGS.md` - Full analysis results
- `MISMATCH_ANALYSIS.md` - Section ID mismatch investigation

These are not used in production but helpful for understanding API behavior.

## Testing

```bash
# Test API connection
python api/test_api.py

# Fetch grades via API
python api/fetch_grades.py

# Compare API vs scraper output
python api/compare_data.py

# Full pipeline test
python test_pipeline.py
```

## Performance Comparison

Real-world timings from testing:

| Operation | docker-containerization | api-polling |
|-----------|------------------------|-------------|
| Full fetch | 2min 30s | 29s |
| Browser startup | 45s | 0s (no browser) |
| Login | 15s | 0.5s (OAuth) |
| Data extraction | 90s | 28.5s (API calls) |
| **Speed improvement** | - | **~6x faster** |

## When to Use api-polling

**Use api-polling if:**
- ✅ Speed is important (6x faster)
- ✅ You have API credentials
- ✅ Reliability is more important than 100% data coverage
- ✅ Teacher comments are not critical
- ✅ You can tolerate formatting noise temporarily

**Use docker-containerization if:**
- ❌ You need 100% of assignments including edge cases
- ❌ Teacher comments are critical for notifications
- ❌ You don't have API credentials
- ❌ You need proven production-ready stability

## Troubleshooting

### API Authentication Errors

```
Error: 401 Unauthorized
```

**Solution:** Check `SCHOOLOGY_API_KEY` and `SCHOOLOGY_API_SECRET` in `.env`

### Section ID Mismatches

```
WARNING: Section ID 7916809753 not in sections list
INFO: Matched 7916809753 to 7916809754 (offset 1)
```

**This is normal.** The API returns different section IDs for grades vs enrollments. The code automatically handles this with fuzzy matching.

### 403 Forbidden on Specific Assignments

```
WARNING: Could not fetch assignment 7981016133 with either ID: 403 Forbidden
```

**This is expected.** Some assignments have permission restrictions. They'll show as "Assignment XXXXXXX" but still include grade data.

### Too Many Changes Detected

```
Changes detected: 102 value(s) changed
```

**This is the known formatting issue.** See `TODO_API_FORMATTING.md`. First notification after switching branches will be noisy.

## Deployment Notes

**This branch is experimental.** For production deployment:

1. Test thoroughly in development first
2. Run manually with `docker compose run` to verify output
3. Check first notification for formatting noise
4. Consider fixing formatting issues in `TODO_API_FORMATTING.md` first
5. Monitor logs closely for first few days

**Recommended:** Keep docker-containerization as production, use api-polling for development/testing until formatting issues are resolved.

## Contributing

If you fix the formatting issues or improve the API integration, please:

1. Update `TODO_API_FORMATTING.md` with completion status
2. Update this README to remove warnings
3. Add test coverage for format normalization
4. Document any new API quirks discovered

## Future Improvements

- [ ] Fix output format to match scraper exactly (see TODO_API_FORMATTING.md)
- [ ] Add retry logic for 403 errors with alternate section IDs
- [ ] Investigate comment endpoint access
- [ ] Add caching layer for assignment/category metadata
- [ ] Consider hybrid approach: API for speed, scraper fallback for comments
- [ ] Reduce Docker image size (currently 1.1GB due to pandas/streamlit)

---

**Last Updated:** 2025-09-30
**Maintainer:** Claude Code + User
