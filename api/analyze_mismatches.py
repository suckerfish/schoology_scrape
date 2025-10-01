#!/usr/bin/env python3
"""
Deep dive analysis of assignment mismatches between API and scraper
"""
import json
import sys
from collections import defaultdict


def analyze_missing_assignments(scraper_file: str, api_file: str):
    """Detailed analysis of why assignments are missing"""

    with open(scraper_file, 'r') as f:
        scraper_data = json.load(f)

    with open(api_file, 'r') as f:
        api_data = json.load(f)

    print("=" * 80)
    print("DETAILED ASSIGNMENT MISMATCH ANALYSIS")
    print("=" * 80)

    # Build assignment indexes with full context
    scraper_assignments = {}
    api_assignments = {}

    # Index scraper data
    for course_name, course in scraper_data.items():
        for period_name, period in course.get('periods', {}).items():
            for category_name, category in period.get('categories', {}).items():
                for assignment in category.get('assignments', []):
                    title = assignment.get('title')
                    scraper_assignments[title] = {
                        'course': course_name,
                        'period': period_name,
                        'category': category_name,
                        'grade': assignment.get('grade'),
                        'comment': assignment.get('comment'),
                        'due_date': assignment.get('due_date')
                    }

    # Index API data
    for course_name, course in api_data.items():
        for period_name, period in course.get('periods', {}).items():
            for category_name, category in period.get('categories', {}).items():
                for assignment in category.get('assignments', []):
                    title = assignment.get('title')
                    api_assignments[title] = {
                        'course': course_name,
                        'period': period_name,
                        'category': category_name,
                        'grade': assignment.get('grade'),
                        'comment': assignment.get('comment'),
                        'due_date': assignment.get('due_date')
                    }

    # Analyze missing in API
    missing_in_api = set(scraper_assignments.keys()) - set(api_assignments.keys())
    missing_in_scraper = set(api_assignments.keys()) - set(scraper_assignments.keys())

    print("\n" + "=" * 80)
    print(f"ASSIGNMENTS IN SCRAPER BUT NOT IN API ({len(missing_in_api)} total)")
    print("=" * 80)

    # Group by course
    by_course = defaultdict(list)
    for title in missing_in_api:
        course = scraper_assignments[title]['course']
        by_course[course].append(title)

    for course, assignments in sorted(by_course.items()):
        print(f"\n{course} ({len(assignments)} assignments missing):")
        print("-" * 80)

        for title in sorted(assignments):
            info = scraper_assignments[title]
            print(f"  Title: {title}")
            print(f"    Grade: {info['grade']}")
            print(f"    Category: {info['category']}")
            if info['due_date']:
                print(f"    Due: {info['due_date']}")
            print()

    # Analyze patterns
    print("\n" + "=" * 80)
    print("PATTERN ANALYSIS - Missing in API")
    print("=" * 80)

    # Pattern 1: Check if missing assignments are "Not graded"
    not_graded_count = sum(
        1 for title in missing_in_api
        if scraper_assignments[title]['grade'] in ['Not graded', 'Missing']
    )

    print(f"\n1. Grading Status:")
    print(f"   Not graded/Missing: {not_graded_count}/{len(missing_in_api)} ({not_graded_count/len(missing_in_api)*100:.1f}%)")

    # Pattern 2: Course distribution
    print(f"\n2. By Course:")
    for course, assignments in sorted(by_course.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"   {course}: {len(assignments)} assignments")

    # Pattern 3: Category distribution
    by_category = defaultdict(int)
    for title in missing_in_api:
        category = scraper_assignments[title]['category']
        by_category[category] += 1

    print(f"\n3. By Category:")
    for category, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
        print(f"   {category}: {count} assignments")

    # Pattern 4: Has due date?
    has_due_date = sum(
        1 for title in missing_in_api
        if scraper_assignments[title]['due_date'] is not None
    )
    print(f"\n4. Due Dates:")
    print(f"   With due date: {has_due_date}/{len(missing_in_api)}")
    print(f"   Without due date: {len(missing_in_api) - has_due_date}/{len(missing_in_api)}")

    # Now analyze missing in scraper (newer assignments)
    print("\n" + "=" * 80)
    print(f"ASSIGNMENTS IN API BUT NOT IN SCRAPER ({len(missing_in_scraper)} total)")
    print("=" * 80)
    print("\nThese are likely assignments added AFTER the scraper ran (Sept 26)")

    by_course_api = defaultdict(list)
    for title in missing_in_scraper:
        course = api_assignments[title]['course']
        by_course_api[course].append(title)

    for course, assignments in sorted(by_course_api.items()):
        print(f"\n{course} ({len(assignments)} assignments):")
        print("-" * 80)

        for title in sorted(assignments):
            info = api_assignments[title]
            print(f"  Title: {title}")
            print(f"    Grade: {info['grade']}")
            print(f"    Category: {info['category']}")
            if info['due_date']:
                print(f"    Due: {info['due_date']}")
            print()

    # Check for entire missing courses
    print("\n" + "=" * 80)
    print("COURSE COMPARISON")
    print("=" * 80)

    scraper_courses = set(scraper_data.keys())
    api_courses = set(api_data.keys())

    print(f"\nScraper courses ({len(scraper_courses)}):")
    for course in sorted(scraper_courses):
        in_api = "✅" if course in api_courses else "❌"
        assignment_count = sum(
            len(cat['assignments'])
            for period in scraper_data[course].get('periods', {}).values()
            for cat in period.get('categories', {}).values()
        )
        print(f"  {in_api} {course} ({assignment_count} assignments)")

    print(f"\nAPI courses ({len(api_courses)}):")
    for course in sorted(api_courses):
        in_scraper = "✅" if course in scraper_courses else "❌"
        assignment_count = sum(
            len(cat['assignments'])
            for period in api_data[course].get('periods', {}).values()
            for cat in period.get('categories', {}).values()
        )
        print(f"  {in_scraper} {course} ({assignment_count} assignments)")

    # Check if Art course exists in API but with no grades
    print("\n" + "=" * 80)
    print("HYPOTHESIS TESTING")
    print("=" * 80)

    if "Art: Section 33" in scraper_courses and "Art: Section 33" not in api_courses:
        print("\n❌ HYPOTHESIS 1: Art course completely missing from API")
        print("   The entire Art course is not returned by the API.")

        # Check scraper Art data
        art_course = scraper_data["Art: Section 33"]
        total_art_assignments = sum(
            len(cat['assignments'])
            for period in art_course.get('periods', {}).values()
            for cat in period.get('categories', {}).values()
        )

        graded_count = 0
        not_graded_count = 0

        for period in art_course.get('periods', {}).values():
            for cat in period.get('categories', {}).values():
                for assignment in cat.get('assignments', []):
                    grade = assignment.get('grade', '')
                    if grade in ['Not graded', 'Missing', '']:
                        not_graded_count += 1
                    else:
                        graded_count += 1

        print(f"   Art assignments in scraper: {total_art_assignments}")
        print(f"   - Graded: {graded_count}")
        print(f"   - Not graded: {not_graded_count}")
        print(f"   Reason: Likely API filters out courses with no numeric grades yet")

    print("\n❌ HYPOTHESIS 2: API excludes assignments without grades")
    ungraded_in_api = sum(
        1 for title in api_assignments
        if api_assignments[title]['grade'] in ['Not graded', 'Missing']
    )
    print(f"   Ungraded assignments in API: {ungraded_in_api}")
    print(f"   Ungraded in scraper but missing in API: {not_graded_count}")
    print(f"   Conclusion: {'CONFIRMED' if ungraded_in_api == 0 else 'PARTIALLY CONFIRMED'}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTotal assignments:")
    print(f"  Scraper: {len(scraper_assignments)}")
    print(f"  API: {len(api_assignments)}")
    print(f"  Matching: {len(set(scraper_assignments.keys()) & set(api_assignments.keys()))}")
    print(f"  Missing in API: {len(missing_in_api)} ({len(missing_in_api)/len(scraper_assignments)*100:.1f}%)")
    print(f"  Missing in Scraper: {len(missing_in_scraper)} ({len(missing_in_scraper)/len(api_assignments)*100:.1f}%)")

    print(f"\nMost likely reasons for missing assignments in API:")
    print(f"  1. Art course not returned by API (27 Art assignments)")
    print(f"  2. Assignments without grades may be filtered")
    print(f"  3. Permission/visibility issues for certain assignment types")


def main():
    if len(sys.argv) < 3:
        print("Usage: python analyze_mismatches.py <scraper_json> <api_json>")
        sys.exit(1)

    scraper_file = sys.argv[1]
    api_file = sys.argv[2]

    analyze_missing_assignments(scraper_file, api_file)


if __name__ == '__main__':
    main()
