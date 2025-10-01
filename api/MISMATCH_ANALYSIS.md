# Assignment Mismatch Deep Dive Analysis

## Key Discovery: Section ID Mismatch Issue

**CRITICAL BUG FOUND AND FIXED:**

The Schoology API has an inconsistency where the section ID returned in the grades endpoint differs from the section ID in the sections/enrollment list.

**Example (Art course):**
- Sections API returns: `7916809754`
- Grades API returns: `7916809753` (off by -1)

**Impact:** Initial fetch missed the entire Art course (27 assignments) because of ID mismatch.

**Solution:** Implemented "fuzzy matching" that checks nearby IDs (±1, ±2) when exact match fails.

---

## Current Status After Fix

### Assignment Coverage

| Source | Total Assignments | Courses |
|--------|------------------|---------|
| **Scraper** (Sept 26) | 72 | 6 |
| **API** (Sept 30, fixed) | 84 | 6 |
| **Matching** | 43 | - |

### Breakdown by Course

| Course | Scraper | API | Status |
|--------|---------|-----|--------|
| Math 7B/8 | 9 | 11 | ✅ API has newer assignments |
| Art | 27 | 30 | ⚠️ API can't fetch assignment details (403) |
| English 7 | 11 | 12 | ✅ API has newer assignments |
| PE 6/7 | 3 | 3 | ✅ Perfect match |
| Science 7 | 14 | 19 | ⚠️ Some 403 errors, but more assignments |
| Social Studies 7 | 8 | 9 | ✅ API has newer assignments |

---

## Missing in API: 27 Assignments

**Pattern Analysis:**

### By Course Distribution:
- **Art**: 25 assignments (93% of missing)
- **English**: 1 assignment
- **Science**: 1 assignment

### By Grading Status:
- **Graded**: 24/27 (89%)
- **Not graded**: 3/27 (11%)

**Conclusion**: The "not graded" hypothesis is **FALSE**. API is missing graded assignments.

### All Art Assignments from Scraper:
1. 2 Continuous Line Contour Drawings - `A+ 5/5` ✅ **Graded**
2. 4 Sea Shell Contour Drawings - `A+ 5/5` ✅ **Graded**
3. Artwork Analysis - `A+ 5/5` ✅ **Graded**
4. Artwork Analysis - Campbell's Soup Cans - `A+ 5/5` ✅ **Graded**
5. Artwork Analysis - The Basket of Apples - `A+ 5/5` ✅ **Graded**
6. Artwork Analysis - The Great Wave of Kanagawa - `A+ 5/5` ✅ **Graded**
7. Artwork Analysis - Untitled Amphora (Jug) from Greece - `A+ 5/5` ✅ **Graded**
8. Backpack Contour Drawing Final - `A 46/48` ✅ **Graded**
9. Backpack Contour Drawing Sketch - `A+ 12/12` ✅ **Graded**
10. Candy Shoes - `A- 23/25` ✅ **Graded**
11. Contour Line - Blind/True Drawing - `A+ 5/5` ✅ **Graded**
12. Contour Line Assessment - `A+ 5/5` ✅ **Graded**
13. Contour Line Drawing Practice Worksheet - `A+ 5/5` ✅ **Graded**
14. Craftsmanship Quality and Neatness Study Worksheet - `B- 4/5` ✅ **Graded**
15. Daily Sketches - `A+ 10/10` ✅ **Graded**
16. **Favorite Food Project and Ode** - `Not graded` ❌ **Ungraded**
17. Mind Map - `A+ 3/3` ✅ **Graded**
18. Notan Positive/Negative Space and Balance Project - `B+ 26.5/30` ✅ **Graded**
19. Notan Project Skills Assessment - `A+ 4/4` ✅ **Graded**
20. Notes and Terms on Space and Balance in Art - `A+ 9/9` ✅ **Graded**
21. **Notes on Warhol Video** - `Not graded` ❌ **Ungraded**
22. Positive/Negative Space Project - `A+ 5/5` ✅ **Graded**
23. Self-Portrait - `A+ 4/4` ✅ **Graded**
24. Set the Scene - `D 2/3` ✅ **Graded**
25. Upsizing Using a Grid - Grasshopper - `A+ 5/5` ✅ **Graded**

**Other Missing:**
- Fig Lang Assessment (English) - `Not graded`
- warm up 8.21.25 (Science) - `A+ 2/2` ✅ **Graded**

---

## Missing in Scraper: 41 Assignments

These fall into two categories:

### 1. Newer assignments (added after Sept 26):
- cw 9/30 Rewriting Literal Equations (Math)
- 7th Figurative Language Quiz (English)
- Periodic Table, PhET States of Matter, Particle Motion (Science)
- Properties of Matter Notes (Science)
- Geography Hunt (Social Studies)

**Total legitimate new assignments**: ~11

### 2. "Assignment XXXXXXXXX" placeholders (403 Forbidden):
- Assignment 7944952427, 7945676466, 7945697977, etc.
- **30 assignments** couldn't fetch details due to 403 errors

**Breakdown of 403 errors by course:**
- **Art**: All 30 Art assignments returned 403 when fetching details
- **Science**: 2 assignments (7981016133, 8057900046)

---

## Root Cause Analysis

### Why Are Art Assignments Showing as "Assignment XXXXXXX"?

**The Problem:**
1. API returns Art course grades successfully (30 assignments with IDs)
2. When trying to fetch assignment details: `GET /sections/{section_id}/assignments/{assignment_id}`
3. **All return 403 Forbidden**

**Hypothesis:**
The section ID mismatch issue affects permissions:
- Grades endpoint: Returns section `7916809753` (works)
- Trying to fetch details from `7916809753` → **403 Forbidden**
- The "real" section ID is `7916809754` (from enrollment)

**Test needed:** Try fetching Art assignment details using the **enrollment section ID** (`7916809754`) instead of the **grades section ID** (`7916809753`).

---

## The Real Question: Which Section ID to Use?

| Endpoint | Section ID to Use | Notes |
|----------|------------------|-------|
| `/users/{user_id}/grades` | Returns its own IDs | May differ from enrollment |
| `/sections/{section_id}/assignments` | Enrollment ID? | Testing needed |
| `/sections/{section_id}/assignments/{id}` | Enrollment ID? | Currently gets 403 with grades ID |

**Action Item:** Modify fetch script to try **both** section IDs when fetching assignment details:
1. Try grades section ID first (current behavior)
2. If 403, try enrollment section ID
3. If still 403, fall back to generic "Assignment XXXXX"

---

## Permission Analysis

### Working Endpoints:
✅ `/users/{user_id}/sections` - Get enrolled courses
✅ `/users/{user_id}/grades` - Get all grades (with mismatched section IDs)
✅ `/sections/{section_id}/assignments` - Get assignment list (for Math, English, Science, Social Studies, PE)
✅ `/sections/{section_id}/grading_categories` - Get categories (for Math, English, Science, Social Studies, PE)

### Failing Endpoints:
❌ `/sections/7916809753/assignments/{id}` - Art assignment details (403)
❌ `/sections/7916809753/grading_categories` - Art categories (403)

**Pattern:** The **grades section ID** (`7916809753`) lacks permission to access assignment and category endpoints.

---

## Recommended Fix

### Update `fetch_grades.py` to use enrollment section ID for detail fetches:

```python
# Build reverse mapping: grades_section_id → enrollment_section_id
enrollment_id_map = {}
for section in sections:
    enrollment_id = section['id']
    # Check all grades for matching course
    for grade_section in all_grades.get('section', []):
        grade_id = grade_section['section_id']
        # Try to match by fuzzy ID logic
        if grade_id == enrollment_id or abs(int(grade_id) - int(enrollment_id)) <= 2:
            enrollment_id_map[grade_id] = enrollment_id
            break

# When fetching assignment details:
def _get_assignment_title(self, grade_section_id: str, assignment_id: str):
    # Try enrollment ID first
    enrollment_id = self.enrollment_id_map.get(grade_section_id, grade_section_id)

    try:
        assignment = self.client.get_assignment_details(enrollment_id, assignment_id)
        return assignment.get('title')
    except:
        # Fallback to grade section ID
        try:
            assignment = self.client.get_assignment_details(grade_section_id, assignment_id)
            return assignment.get('title')
        except:
            return f'Assignment {assignment_id}'
```

---

## Summary

### Issue #1: Section ID Mismatch ✅ **FIXED**
- **Problem:** Grades API returns different section IDs than enrollment API
- **Solution:** Fuzzy matching with ±2 offset
- **Result:** Now fetches all 6 courses including Art

### Issue #2: Permission Errors on Art Details ⚠️ **NEEDS FIX**
- **Problem:** Can't fetch assignment details using grades section ID (`7916809753`)
- **Likely Cause:** Need to use enrollment section ID (`7916809754`) for detail requests
- **Solution:** Try enrollment ID first, fall back to grades ID
- **Impact:** 30/84 assignments (36%) showing as "Assignment XXXXX"

### Issue #3: Comments Not Available ❌ **API LIMITATION**
- **Problem:** API doesn't expose teacher grade comments reliably
- **Workaround:** Use scraper for comments when needed
- **Impact:** Critical for notifications

---

## Next Steps

1. **Implement enrollment ID fallback** for assignment detail fetches
2. **Re-run fetch** and verify all Art assignments get proper titles
3. **Re-run comparison** to get accurate mismatch count
4. **Document final findings** for decision on API vs hybrid approach

---

## Expected Outcome After Fix

If enrollment ID fix works:
- **API should retrieve ~84 assignments** with proper titles
- **Match rate should increase** from 43/72 (60%) to ~70/72 (97%)
- **Only real mismatches** would be:
  - Assignments added after Sept 26 (API has newer data)
  - Assignments removed/hidden since Sept 26 (scraper has old data)
