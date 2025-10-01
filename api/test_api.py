#!/usr/bin/env python3
"""
Quick test of API client to verify credentials and basic functionality
"""
import logging
from client import SchoologyAPIClient

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Test API client"""
    try:
        print("=" * 80)
        print("Testing Schoology API Client")
        print("=" * 80)

        # Initialize client
        print("\n1. Initializing API client...")
        client = SchoologyAPIClient()
        print("   ✅ Client initialized")

        # Get user ID
        print("\n2. Getting user ID...")
        user_id = client.get_user_id()
        print(f"   ✅ User ID: {user_id}")

        # Get sections
        print("\n3. Getting enrolled sections...")
        sections = client.get_sections()
        print(f"   ✅ Found {len(sections)} sections:")
        for section in sections[:5]:  # Show first 5
            print(f"      - {section.get('course_title')} ({section.get('id')})")
        if len(sections) > 5:
            print(f"      ... and {len(sections) - 5} more")

        # Get grades
        print("\n4. Getting grades...")
        grades = client.get_grades()
        total_assignments = sum(
            len(period.get('assignment', []))
            for section in grades.get('section', [])
            for period in section.get('period', [])
        )
        print(f"   ✅ Found {total_assignments} graded assignments")

        # Test getting assignments for first section
        if sections:
            section_id = sections[0]['id']
            print(f"\n5. Testing assignment fetch for first section ({section_id})...")
            assignments = client.get_assignments(section_id)
            print(f"   ✅ Found {len(assignments)} assignments")

            if assignments:
                # Test comment fetch for first assignment
                assignment_id = str(assignments[0]['id'])
                print(f"\n6. Testing comment fetch for first assignment ({assignment_id})...")
                comments = client.get_assignment_comments(section_id, assignment_id)
                print(f"   ✅ Found {len(comments)} comments")

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED - API client is working!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        logger.error("Test failed", exc_info=True)
        raise


if __name__ == '__main__':
    main()
