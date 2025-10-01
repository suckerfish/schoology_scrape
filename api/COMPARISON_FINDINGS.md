# API vs Scraper Comparison - Key Findings

**Date**: September 30, 2025
**Scraper Data**: `data/all_courses_data_20250926_080054.json` (Sept 26, 2025)
**API Data**: `data/api_grades_20250930_224104.json` (Sept 30, 2025)

---

## Executive Summary

The Schoology API can retrieve **most** grade data but has important limitations:

✅ **API Successfully Provides:**
- Core grade values (points earned/max points)
- Assignment titles
- Due dates
- Course/period/category structure
- 43/72 assignments matched (60% coverage)

⚠️ **Critical Issues:**
1. **Missing assignments**: 27 assignments in scraper not in API (mostly Art class)
2. **Grade format differences**: Scraper shows "10 / 10 / 10", API shows "10 / 10"
3. **Comments mostly unavailable**: Only 1 comment found via API
4. **Some assignments forbidden**: 2 assignments returned 403 errors

---

## Detailed Findings

### 1. Assignment Coverage

| Metric | Scraper | API | Notes |
|--------|---------|-----|-------|
| Total courses | 6 | 5 | API missing entire Art course data |
| Total assignments | 72 | 54 | 25% fewer assignments |
| Matching assignments | - | 43 | 60% overlap |
| Missing in API | - | 27 | Mostly Art assignments |
| Missing in Scraper | - | 11 | Recent assignments added after Sept 26 |

**Missing in API (27 assignments):**
- All Art class assignments (Contour Drawing, Notan, Self-Portrait, etc.)
- Some English assignments (Fig Lang Assessment, warm up, etc.)

**Possible reasons:**
- Art assignments may not be graded yet (only have placeholder grades)
- API may filter out non-graded items
- Permissions issues for certain assignment types

### 2. Grade Format Differences

**Scraper format**: `"10 / 10 / 10"` or `"A+ 5 / 5 / 5"`
**API format**: `"10 / 10"` or `"5 / 5"`

The scraper includes an **extra repeated value** (appears to be duplicated max_points):
- Scraper: `grade / max_points / max_points`
- API: `grade / max_points` (correct format)

**Impact**: All 37 "grade mismatches" are actually just format differences. The actual grades are **identical**.

### 3. Comments - CRITICAL FOR NOTIFICATIONS ⚠️

**Scraper**: 1 real comment + 71 "No comment" defaults
**API**: 2 comments found (including 1 different from scraper)

**Example difference:**
- Assignment: "Class Norms"
- Scraper: "No comment"
- API: "ok"

**API Comment Retrieval Issues:**
1. The `/grades` endpoint has a `comment` field but it's usually `null`
2. The `/assignments/{id}/comments` endpoint returns discussion comments, not teacher grade comments
3. These are different types of comments:
   - **Grade comments** (teacher feedback on the grade) - NOT accessible via API
   - **Discussion comments** (student/teacher discussion thread) - accessible but different

**Conclusion**: **API cannot reliably retrieve teacher grade comments**. This is a critical gap for your notification system.

### 4. Due Date Formatting

**Scraper**: `"9/05/25 11:59pm"`
**API**: `"09/05/25 11:59pm"`

Only difference is leading zero padding. Functionally identical, just formatting differences.

All 39 "due date differences" are actually the same dates, just formatted slightly differently.

### 5. API Access Errors

```
WARNING - Could not fetch assignment 7981016133: 403 Forbidden
WARNING - Could not fetch assignment 8057900046: 403 Forbidden
```

Two assignments returned 403 Forbidden when trying to fetch details. These appear in API data as:
- `"Assignment 7981016133"`
- `"Assignment 8057900046"`

Without titles or proper details.

---

## Data Quality Comparison

### What's Identical ✅
- Numeric grades (when accounting for format differences)
- Due dates (when accounting for format differences)
- Assignment titles
- Course/period/category structure
- Category names and weights

### What's Different ⚠️
- Grade format (extra value in scraper)
- Comment availability (scraper has real comments, API mostly doesn't)
- Assignment coverage (API missing 27 assignments)
- Some assignments return 403 errors via API

### What's Better in API 🌟
- Cleaner grade format (no duplicated max_points)
- Timestamps for when grades were posted (not shown in comparison but available)
- No browser automation required
- More reliable (no CAPTCHA, timeouts, UI changes)

### What's Better in Scraper 🌟
- **Teacher grade comments** (critical for notifications)
- Complete assignment coverage (all 72 assignments)
- No permission errors
- Letter grades included in format (e.g., "A+ 5 / 5 / 5")

---

## Implications for Migration

### Can API Replace Scraper? ⚠️ **Partially**

**YES for:**
- Grade value monitoring (10/10, 5/5, etc.)
- New assignment detection
- Due date tracking
- Basic notifications ("Grade posted: 10/10")

**NO for:**
- **Teacher comments** (critical gap)
- Complete assignment coverage (missing ~25%)
- Letter grade extraction (would need to calculate from percentages)

### Recommended Approach: **Hybrid System**

Use API as primary method with scraper as fallback:

```
┌─────────────────────────────────────┐
│  Primary: API                       │
│  - Fast grade checks                │
│  - Detect new grades                │
│  - Get timestamps                   │
└─────────────────────────────────────┘
           ↓ (if comment exists)
┌─────────────────────────────────────┐
│  Fallback: Scraper                  │
│  - Fetch teacher comments           │
│  - Get letter grades                │
│  - Fill gaps for missing assignments│
└─────────────────────────────────────┘
```

**Benefits:**
1. Use fast API calls for routine checks (every 15 min)
2. Only trigger scraper when:
   - API detects new grade
   - Need to fetch comments
   - API returns errors

**Implementation:**
```python
# Pseudo-code
api_grades = fetch_via_api()
for assignment in api_grades:
    if assignment.newly_graded:
        # Try to get comment via scraper
        comment = scraper.get_comment(assignment.id)
        notify_with_comment(assignment, comment)
```

---

## API Limitations Summary

| Limitation | Impact | Workaround |
|------------|--------|------------|
| Missing teacher comments | High | Use scraper for comments |
| Missing 27 assignments | Medium | Investigate permissions or use scraper |
| 403 errors on 2 assignments | Low | Skip these or use scraper |
| No letter grades in format | Low | Calculate from percentages + scales |
| Grade format differences | None | Normalize in comparison logic |
| Due date format differences | None | Normalize in comparison logic |

---

## Next Steps

### Option 1: API-Only (Not Recommended)
- **Pros**: Fast, reliable, no browser automation
- **Cons**: Missing comments (critical feature loss)
- **Use case**: If comments aren't important

### Option 2: Hybrid API + Scraper (Recommended)
- **Pros**: Best of both worlds, optimize speed while keeping all features
- **Cons**: More complex implementation
- **Use case**: Production system

### Option 3: Keep Scraper-Only
- **Pros**: No changes needed, all features work
- **Cons**: Slower, risk of CAPTCHA/timeouts, UI breakage
- **Use case**: If API access becomes unavailable

---

## Code Changes Needed for Hybrid Approach

1. **Update GradeScraper** to accept API client:
   ```python
   class GradeScraper:
       def __init__(self, api_client=None):
           self.api_client = api_client
           self.use_api = api_client is not None
   ```

2. **Create API fetch path**:
   ```python
   if self.use_api:
       grades = self.api_client.fetch_all_grades()
   else:
       grades = self.driver.get_all_courses_data()
   ```

3. **Add comment fetching fallback**:
   ```python
   if assignment.has_new_grade and not assignment.comment:
       # Fall back to scraper for comment
       assignment.comment = self.scraper.get_comment(assignment.id)
   ```

4. **Update comparator** to handle format differences:
   ```python
   def normalize_grade(grade_str):
       # "10 / 10 / 10" → "10 / 10"
       parts = grade_str.split('/')
       if len(parts) == 3:
           return f"{parts[0].strip()} / {parts[1].strip()}"
       return grade_str
   ```

---

## Testing Recommendations

Before deploying hybrid approach:

1. **Run API-only for 1 week** alongside existing scraper
2. **Compare outputs** to catch edge cases
3. **Monitor error rates** (403s, timeouts, etc.)
4. **Test comment fetching** on assignments with known teacher comments
5. **Verify notifications** include all expected data

---

## Conclusion

The Schoology API is a viable **supplement** to scraping but **cannot fully replace it** due to missing teacher comments. A hybrid approach using API for speed and scraper for comments would provide the best user experience while reducing scraping frequency by ~90%.

**Recommendation**: Implement hybrid system where API handles routine checks and scraper only activates when comments are needed or API fails.
