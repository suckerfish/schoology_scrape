# Schoology API Module

REST API client for fetching grade data from Schoology.

## Setup

1. **Get API credentials** from Schoology (requires school admin):
   - Log into Schoology as admin
   - Go to Tools → School Management → API
   - Create new API key/secret pair

2. **Add credentials to `.env`**:
   ```bash
   SCHOOLOGY_API_KEY=your-api-key
   SCHOOLOGY_API_SECRET=your-api-secret
   SCHOOLOGY_DOMAIN=yourdomain.schoology.com
   ```

## Files

- **`client.py`** - Schoology API client with OAuth 1.0a authentication
- **`fetch_grades.py`** - Legacy grade fetcher (dict-based output)
- **`fetch_grades_v2.py`** - Current grade fetcher (Pydantic models with IDs)

## API Endpoints Used

- `/users/me` - Get current user ID
- `/users/{user_id}/sections` - Get enrolled courses
- `/users/{user_id}/grades` - Get all grades with timestamps
- `/sections/{section_id}/assignments` - Get assignment details
- `/sections/{section_id}/grading_categories` - Get category names and weights

## Usage

The main entry point is `fetch_grades_v2.py` which returns Pydantic models:

```python
from api.fetch_grades_v2 import APIGradeFetcherV2

fetcher = APIGradeFetcherV2()
grade_data = fetcher.fetch_all_grades()  # Returns GradeData model

for section in grade_data.sections:
    print(f"{section.course_title}: {len(section.periods)} periods")
```

## Known Limitations

- Some assignments return 403 Forbidden (permission restrictions)
- Section IDs from grades endpoint sometimes differ from enrollments (handled with fuzzy matching)
- Teacher comments less available than web scraping
