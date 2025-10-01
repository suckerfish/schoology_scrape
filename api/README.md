# Schoology API Module

Alternative to web scraping using Schoology's official REST API.

## Setup

1. **Get API credentials** from Schoology (requires school admin):
   - Log into Schoology as admin
   - Go to App Center → School App Management → API Keys
   - Create new API key/secret pair

2. **Add credentials to `.env`**:
   ```bash
   SCHOOLOGY_API_KEY=your-api-key
   SCHOOLOGY_API_SECRET=your-api-secret
   SCHOOLOGY_DOMAIN=lvjusd.schoology.com
   ```

3. **Install dependencies**:
   ```bash
   uv pip install requests-oauthlib
   ```

## Usage

### Fetch Grade Data

```bash
cd api/
python fetch_grades.py
```

This fetches all grade data via API and saves to `data/api_grades_YYYYMMDD_HHMMSS.json` in the same format as the scraper output.

### Compare API vs Scraper Data

```bash
cd api/
python compare_data.py ../data/all_courses_data_20250310_080030.json ../data/api_grades_20250330_100000.json
```

Generates detailed comparison report showing:
- Missing assignments in either dataset
- Grade mismatches
- Comment differences (critical for notifications)
- Due date differences

Report saved to `data/api_scraper_comparison.json`

## Files

- **`client.py`** - Schoology API client with OAuth 1.0a authentication
- **`fetch_grades.py`** - Fetch and structure grade data matching scraper format
- **`compare_data.py`** - Compare API data vs scraper data to identify deltas

## API Endpoints Used

Based on research in `/Users/chad/Documents/PythonProject/schoology_api/`:

- `/users/me` - Get current user ID
- `/users/{user_id}/sections` - Get enrolled courses
- `/users/{user_id}/grades` - Get all grades with timestamps
- `/sections/{section_id}/assignments` - Get assignment details (titles, due dates)
- `/sections/{section_id}/assignments/{assignment_id}/comments` - Get teacher comments
- `/sections/{section_id}/grading_categories` - Get category names and weights

## Key Differences: API vs Scraper

### Advantages of API:
- ✅ Faster (direct REST calls vs browser automation)
- ✅ More reliable (no CAPTCHA, session timeouts, or UI changes)
- ✅ Structured JSON data (no HTML parsing)
- ✅ Timestamps for when grades were posted (change detection)
- ✅ Official interface (won't break)

### Potential Issues:
- ⚠️  Teacher comments may not be available via API (field exists but often null)
- ⚠️  Requires API credentials from school admin
- ⚠️  Some historical assignments might not be returned

## Next Steps

After running comparison:
1. Review `data/api_scraper_comparison.json` for critical deltas
2. If comments are missing, may need hybrid approach (API for grades, scraper for comments)
3. If API data is sufficient, can replace scraper with API client
4. Update pipeline to use API client instead of Playwright driver
