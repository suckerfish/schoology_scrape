# API Polling Branch - Formatting Issues to Fix

**Priority:** High - False positive change detection undermines the entire monitoring system

## Problem Summary

The API fetcher outputs data in a slightly different format than the scraper, causing the diff detector to flag 100+ "changes" when nothing actually changed. This creates noise and defeats the purpose of change notifications.

## Specific Format Mismatches

### 1. Grade Format - Three vs Two Numbers
- **Scraper:** `"10 / 10 / 10"` (score / max / total)
- **API:** `"10 / 10"` (score / max)
- **Fix location:** `api/fetch_grades.py:_format_grade()` around line 27-38
- **Solution:** Match scraper's three-number format

### 2. Date Format - Leading Zeros
- **Scraper:** `"8/20/25 3:59pm"` (no leading zeros)
- **API:** `"08/20/25 03:59pm"` (with leading zeros)
- **Fix location:** `api/fetch_grades.py:_format_timestamp()` around line 40-46
- **Solution:** Use format string `'%-m/%-d/%y %-I:%M%p'` (dash removes leading zeros on Unix/Mac)
  - **Note:** Windows doesn't support `%-` format, use `.replace('0', '', 1)` conditionally

### 3. Category Names - Inconsistent Weight Display
- **Scraper:** Consistently includes weights: `"Class Projects (30%)"`
- **API:** Sometimes includes, sometimes omits weights
- **Fix location:** `api/fetch_grades.py:_get_category_name()` around line 119-154
- **Solution:** Always include weight percentage in parentheses when available

### 4. Category Grade vs Not Calculated
- **Scraper:** May use different text for ungraded categories
- **API:** Uses "Not calculated"
- **Fix location:** Throughout `api/fetch_grades.py` in category_grade assignments
- **Solution:** Match scraper's exact wording

## Implementation Steps

1. **Read scraper output** to understand exact format:
   ```bash
   cat data/all_courses_data_20250926_080054.json | jq '.["Science 7: Section 8"].periods'
   ```

2. **Update `api/fetch_grades.py`:**
   - Fix `_format_grade()` to return three-number format
   - Fix `_format_timestamp()` to remove leading zeros
   - Fix `_get_category_name()` to consistently include weights
   - Fix category_grade text to match scraper

3. **Test with comparison:**
   ```bash
   # Run API fetch
   python api/fetch_grades.py

   # Compare with latest scraper output
   python api/compare_data.py

   # Should show minimal/no formatting differences
   ```

4. **Delete false positive data files** after fix to start fresh

5. **Verify in Docker:**
   ```bash
   docker compose run --rm schoology-scheduler python -u main.py
   # Should show "No changes detected" or only real changes
   ```

## Files to Modify

- `api/fetch_grades.py` - Primary formatting fixes
- Possibly `pipeline/comparator.py` - If normalization before comparison is preferred

## Testing Checklist

- [ ] Grade format matches: `X / X / X` pattern
- [ ] Dates match: no leading zeros on month/day/hour
- [ ] Category names consistent with weights
- [ ] Category grades use same "Not graded" text
- [ ] Run full comparison shows <5 differences (only real data changes)
- [ ] Test in Docker container
- [ ] Verify notifications only trigger on real changes

## Alternative Approach

Instead of fixing the API output, could normalize BOTH formats in the comparator before diffing. This would be more robust but requires changes to `pipeline/comparator.py` instead.

**Pros:** Works regardless of data source format
**Cons:** More complex, hides the underlying format mismatch

## Expected Outcome

After fixes, running the API polling branch twice in a row with no real grade changes should result in:
- "No changes detected" message
- No notifications sent
- Only new assignments or actual grade changes trigger alerts

## Current Status

- [x] Issue identified and documented
- [x] Formats analyzed and exact patterns determined
- [x] Code fixes implemented (OR scraper format changed to match API)
- [x] Testing completed - No format mismatches found as of 2025-10-01
- [x] Deployed to production

## Resolution (2025-10-01)

**Status: RESOLVED** ✅

Comparison testing shows that the API output now matches the scraper output exactly:
- **Grades:** Both use 2-number format ("10 / 10")
- **Dates:** Both use format with leading zeros ("08/15/25 03:00pm")
- **Categories:** Both use consistent naming with weights
- **All 82 assignments match** between API and scraper

The format issues described in this document were either:
1. Fixed in the API implementation (api/fetch_grades.py)
2. Or the scraper format changed between 2025-09-26 and 2025-09-30

**Testing Results:**
```bash
$ python3 api/compare_data.py data/all_courses_data_20250930_231843.json data/api_grades_20250930_225113.json

✅ 82 assignments found in BOTH datasets
✅ All grades MATCH between scraper and API
✅ All comments MATCH
✅ No critical issues - API data matches scraper data
```

**Note:** Historical data from 2025-09-26 shows the old scraper used 3-number format with letter grades ("B- 8 / 10 / 10") and dates without leading zeros ("8/27/25 4:59pm"). The current scraper format has converged with the API format.

---

**Created:** 2025-09-30
**Resolved:** 2025-10-01
**Branch:** api-polling
**Impact:** None - formats now match correctly
