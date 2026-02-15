# Codebase Concerns

**Analysis Date:** 2026-02-14

## Error Handling - Bare Except Clauses

**Issue:** Multiple modules use bare `except:` clauses which swallow all exceptions including system interrupts

**Files:**
- `api/fetch_grades_v2.py` (lines 68, 74, 93, 196)
- `shared/models.py` (lines 43, 66, 138)
- `api/fetch_grades.py` (line 144)

**Impact:** Silent failures make debugging difficult. KeyboardInterrupt and SystemExit can be caught unexpectedly. Parsing failures (Decimal, datetime) are logged but exception details are lost.

**Fix approach:**
- Replace bare `except:` with specific exception types (`ValueError`, `DecimalException`, `TypeError`)
- Preserve exception details in logging for troubleshooting
- Allow system exceptions (KeyboardInterrupt, SystemExit) to propagate

---

## Known Limitations - 403 Forbidden on Assignments

**Issue:** ~5 assignments per semester consistently return 403 Forbidden from Schoology API

**Symptom:** `_get_assignment_title()` in `api/fetch_grades_v2.py` (lines 118-148) logs warnings for specific assignments, then falls back to generic title

**Current mitigation:**
- Code attempts both enrollment_id and grade_section_id (lines 128-141)
- Falls back to generic `Assignment {id}` title if both fail

**Why it persists:** This is a Schoology API permission issue - teacher hasn't granted access to specific assignments

**Workaround:** No fix possible without Schoology API changes or teacher granting permissions

---

## Fragile Areas - Bare Except with Silent Pass

**Issue:** Bare `except: pass` in `api/fetch_grades_v2.py` line 196-197 hides weight parsing failures

```python
try:
    weight_decimal = Decimal(str(weight))
except:
    pass  # Silent failure - no logging
```

**Files:** `api/fetch_grades_v2.py` (line 196-197)

**Impact:** Category weight becomes None without any warning. Silent data loss could cause unexpected behavior in grade calculations if weights are ever used.

**Safe modification:** Add logging at minimum; preferably specify exception type:
```python
except (ValueError, TypeError):
    logger.debug(f"Could not parse weight {weight}, using None")
    pass
```

---

## Database Concurrency Issue

**Issue:** SQLite default timeout is very short, can cause "database is locked" errors under concurrent access

**Files:** `shared/grade_store.py` (lines 43-54)

**Current implementation:**
```python
conn = sqlite3.connect(self.db_path)  # No timeout parameter
```

**Risk:** If multiple processes/threads try to write simultaneously (Docker container restart + scheduled run), database lock contention causes failures.

**Scaling path:**
- Add timeout parameter: `sqlite3.connect(self.db_path, timeout=30.0)`
- Consider WAL mode (Write-Ahead Logging) for better concurrent access
- For production scale, migrate to PostgreSQL

---

## API Client Error Handling

**Issue:** `api/client.py` `_get()` method (line 47-50) calls `response.raise_for_status()` without distinguishing error types

```python
response = self.session.get(url)
response.raise_for_status()  # Raises HTTPError for any status >= 400
```

**Impact:**
- 403 errors (permission denied) treated same as 500 (server error)
- 429 (rate limit) has no retry logic
- Network timeouts cause pipeline failure without retries

**Improvement path:**
- Add per-error-code handling in `get_assignment_details()` and `get_assignment_comments()`
- Implement exponential backoff for 429/503 responses
- Log context (assignment_id, section_id) with each error for debugging

---

## Test Coverage Gaps

**Untested areas:**

1. **Enrollment ID offset matching logic** (`api/fetch_grades_v2.py` lines 238-247)
   - Section ID offset matching is automatic but never tested
   - If offset logic is wrong, sections silently use wrong enrollment_id
   - Files: `api/fetch_grades_v2.py` (lines 238-247)

2. **Change detection edge cases** (`shared/id_comparator.py`)
   - What happens when assignment_id changes for same content?
   - What if category_id changes?
   - Files: `shared/id_comparator.py` (lines 188-247)

3. **Decimal/number parsing in real API data** (`api/fetch_grades_v2.py` lines 31-77, `shared/models.py` lines 35-44)
   - Only tested with mock data or specific formats
   - Real API might return unexpected types (null, empty string variations)
   - Files: `api/fetch_grades_v2.py`, `shared/models.py`

4. **Database state recovery**
   - No tests for database corruption or incomplete snapshots
   - `clear_all_data()` exists but only for testing
   - Files: `shared/grade_store.py` (lines 358-367)

5. **Concurrent pipeline runs**
   - Scheduler allows overlapping runs if fetch takes longer than interval
   - No file locking or database transaction isolation
   - Files: `main.py`, `pipeline/orchestrator_v2.py`

**Risk:** Medium - these gaps could cause silent failures or data corruption under edge conditions

---

## Performance Bottleneck - API Client Caching

**Issue:** Assignment details and grading categories are cached in memory per fetcher instance

**Current code:** `api/fetch_grades_v2.py` (lines 26-28)
```python
self.categories_cache = {}
self.assignments_cache = {}
self.enrollment_id_map = {}
```

**Problem:**
- Cache is never invalidated (could serve stale data across multiple runs in daemon mode)
- Cache lives for lifetime of APIGradeFetcherV2 instance
- New instance created per pipeline run, so cache only helps within single run

**Current capacity:** Caches one full fetch only; no performance benefit for typical usage (one fetch per run)

**Improvement path:**
- Add cache invalidation on new pipeline run
- For daemon mode: implement time-based cache expiration (e.g., 1 hour)
- Use shared cache if merging daemon runs

---

## Change Detection - Only IDs Matter

**Issue:** `shared/id_comparator.py` relies entirely on `assignment_id` being stable across API calls

**Files:** `shared/id_comparator.py` (lines 138-247)

**Current assumption:**
- Same assignment_id = same assignment
- All metadata (title, category_id) can change without triggering false positives

**Risk:** If Schoology renumbers assignment IDs (unlikely but possible during schema updates), system won't detect any changes or will detect everything as new.

**Mitigation:** None currently. No API version checking or schema validation.

**Testing needed:** Verify assignment_id stability over semester

---

## Logging - No Request/Response Logging

**Issue:** API calls have no logging of request parameters or response data

**Files:** `api/client.py` (lines 42-50)

```python
def _get(self, endpoint: str) -> Dict[str, Any]:
    url = f'{self.BASE_URL}/{endpoint}'
    self.logger.debug(f"GET {url}")  # Only logs URL
    response = self.session.get(url)
    response.raise_for_status()
    return response.json()
```

**Impact:**
- Hard to debug API failures (what was the response status? response body?)
- Rate limiting not visible until it fails
- No visibility into how many API calls per run

**Improvement:**
- Log response status and timing
- Log error responses before raise_for_status()
- Track API call count and timing

---

## Database Schema - TEXT for Numeric Data

**Issue:** `shared/grade_store.py` stores numeric data as TEXT instead of native types

**Files:** `shared/grade_store.py` (lines 105-119)

**Schema:**
```sql
earned_points TEXT,      -- should be REAL or DECIMAL
max_points TEXT,         -- should be REAL or DECIMAL
weight TEXT              -- should be REAL
```

**Impact:**
- Queries can't use numeric comparisons without casting
- Sorting by grade requires string sort (10 < 2)
- Storage overhead (text is larger than binary)

**Why TEXT was chosen:** Pydantic Decimal fields need string serialization for JSON compatibility

**Fix approach:**
- Store numeric fields as REAL in SQLite (no precision loss for grades/weights)
- Convert to/from Decimal at ORM layer only
- Maintain backward compatibility with existing data

---

## Notification System - No Provider Failover

**Issue:** If one notification provider fails, others may not be attempted

**Files:** `notifications/manager.py` (lines 92-115)

**Current behavior:** Each provider is called independently, but failures don't prevent other providers from sending

**Gap:** If email provider crashes during send, subsequent Pushover attempts might still work. But logging of partial failures is unclear.

**Improvement:** Add explicit success/failure tracking per provider and log aggregated results

---

## State Comparison - Initial Snapshot Not Marked

**Issue:** First data capture is marked `is_initial=True` but might actually contain changes if user already had grades

**Files:** `shared/id_comparator.py` (lines 149-161)

```python
if is_initial:
    self.logger.info("No previous data found - treating as initial capture")
    if save_to_db:
        self.store.save_grade_data(new_data)
    return ChangeReport(..., is_initial=True)
```

**Impact:** First run will never send change notifications, even if there are assignments with grades ready to be tracked

**Acceptable tradeoff:** This is intentional behavior (don't spam on first run), but worth documenting as limitation

---

## Dependencies at Risk - google-genai Migration

**Issue:** Recently migrated from deprecated `google-generativeai` to `google-genai` SDK

**Files:**
- Recent commit shows migration: "Migrate to google-genai SDK"
- `notifications/gemini_provider.py` depends on new SDK

**Risk:** New SDK may have different API, rate limits, or failure modes than old one. Limited production history.

**Mitigation:**
- Gemini provider gracefully degrades if API fails (errors logged, notifications proceed without AI analysis)
- Notifications don't fail if Gemini is unavailable

**Recommendation:** Monitor Gemini provider logs in first month after deployment

---

## Empty Database on First Run

**Issue:** If database file is deleted but application continues running, next comparison might fail silently

**Files:** `shared/grade_store.py` (lines 56-135)

**Current behavior:**
- `_init_db()` creates schema if not exists
- `detect_changes()` calls `get_latest_snapshot_time()` which returns None if database is empty
- Treated as initial capture, no changes detected

**Risk:** If database corruption occurs mid-run, could cause all changes to be missed in next run

**Mitigation:**
- Schema is recreated on open (idempotent)
- Initial run handles missing data gracefully
- No data corruption detected until comparison happens

**Improvement:** Add database integrity check on startup

---

## Healthcheck Integration - Silent Failure

**Issue:** `pipeline/orchestrator_v2.py` (lines 227-247) pings healthchecks.io but failures are only warned, not propagated

```python
def _ping_healthcheck(self, success: bool = True, message: str = "") -> None:
    # ...
    except Exception as e:
        self.logger.warning(f"Failed to ping healthchecks.io: {e}")  # Silently continues
```

**Impact:** If healthchecks.io endpoint is wrong or network is down, system appears healthy but no monitoring

**Current state:** HEALTHCHECKS_URL is optional (checked at line 235-237), so this is graceful degradation

**Recommendation:** Log at INFO level, not WARNING, for optional external services

---

## Section ID Offset Matching - Potential Silent Mismatch

**Issue:** Offset matching logic in `api/fetch_grades_v2.py` (lines 238-247) tries -1, 1, -2, 2 offsets but has no mechanism to verify match is correct

```python
for offset in [-1, 1, -2, 2]:
    nearby_id = str(int(grade_section_id) + offset)
    if nearby_id in section_map:
        logger.info(f"  Matched {grade_section_id} to {nearby_id}")
        section_info = section_map[nearby_id]
        break
```

**Risk:** If multiple section IDs are nearby, first match wins even if wrong section

**Example:** grade_section_id=100 might match either 99 or 101 or 102, but code takes first

**Mitigation:**
- This is a known Schoology API quirk (mentioned in CLAUDE.md)
- Matching is logged for debugging
- Manual verification needed if sections are misaligned

**Improvement:** Add matching confidence score based on course_title similarity

