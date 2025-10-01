#!/usr/bin/env python3
"""
Debug script to investigate why Art course is missing from API
"""
import json
import logging
from client import SchoologyAPIClient

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def main():
    print("=" * 80)
    print("DEBUG: Art Course Investigation")
    print("=" * 80)

    client = SchoologyAPIClient()

    # Get all sections
    print("\n1. Fetching all sections...")
    sections = client.get_sections()

    print(f"\nFound {len(sections)} sections:")
    for section in sections:
        print(f"  - {section.get('course_title')} ({section.get('id')})")
        print(f"    Section title: {section.get('section_title')}")
        print(f"    Active: {section.get('active')}")

    # Look for Art course
    art_section = None
    for section in sections:
        if 'Art' in section.get('course_title', ''):
            art_section = section
            print(f"\n✅ Found Art course:")
            print(json.dumps(section, indent=2))
            break

    if not art_section:
        print("\n❌ Art course NOT found in sections list!")
        print("\nPossible reasons:")
        print("  1. Course is marked inactive")
        print("  2. User not enrolled in Art for current term")
        print("  3. API permissions don't include this course")
        return

    # Try to get grades for Art course
    art_section_id = art_section['id']
    print(f"\n2. Fetching grades for Art section {art_section_id}...")

    try:
        grades = client.get_grades(section_id=art_section_id)
        print("✅ Successfully fetched Art grades!")
        print(json.dumps(grades, indent=2)[:1000])

        # Count assignments
        total_assignments = 0
        for section in grades.get('section', []):
            for period in section.get('period', []):
                assignments = period.get('assignment', [])
                total_assignments += len(assignments)

        print(f"\n📊 Art course has {total_assignments} graded assignments in API")

    except Exception as e:
        print(f"❌ Failed to fetch Art grades: {e}")

    # Try to get assignments for Art course
    print(f"\n3. Fetching assignments for Art section {art_section_id}...")

    try:
        assignments = client.get_assignments(art_section_id)
        print(f"✅ Successfully fetched {len(assignments)} Art assignments!")

        if assignments:
            print("\nFirst 5 assignments:")
            for assignment in assignments[:5]:
                print(f"  - {assignment.get('title')} (ID: {assignment.get('id')})")
                print(f"    Max points: {assignment.get('max_points')}")
                print(f"    Published: {assignment.get('published')}")
                print(f"    Completed: {assignment.get('completed')}")
                print()

    except Exception as e:
        print(f"❌ Failed to fetch Art assignments: {e}")

    # Compare with all grades fetch
    print("\n4. Checking if Art appears in 'all grades' fetch...")
    all_grades = client.get_grades()

    art_in_all_grades = False
    for section in all_grades.get('section', []):
        if section['section_id'] == art_section_id:
            art_in_all_grades = True
            print(f"✅ Art course IS in all grades response")
            print(f"   Section: {json.dumps(section, indent=2)[:500]}")
            break

    if not art_in_all_grades:
        print("❌ Art course NOT in all grades response")
        print("\nAll section IDs in grades response:")
        for section in all_grades.get('section', []):
            print(f"  - {section['section_id']}")


if __name__ == '__main__':
    main()
