#!/usr/bin/env python3
"""
Test script to verify that the fixed comparator would catch the Bedouin Presentation
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.comparator import GradeComparator

def test_bedouin_detection():
    """Test that the Bedouin Presentation would be detected with the fix"""

    # Load the historical data files
    remote_data_dir = Path("/Users/chad/Library/CloudStorage/ShellFish/ampere/dockers/komodo-agent/stacks/schoology-api-ampere/data")

    # Before: 11/05 12:00 (no Bedouin)
    before_file = remote_data_dir / "all_courses_data_20251105_120045.json"
    # After: 11/05 19:00 (Bedouin appears with grade 32/50)
    after_file = remote_data_dir / "all_courses_data_20251105_190047.json"

    if not before_file.exists() or not after_file.exists():
        print(f"ERROR: Data files not found")
        print(f"Before: {before_file}")
        print(f"After: {after_file}")
        return False

    print(f"Loading data files...")
    print(f"Before: {before_file}")
    print(f"After: {after_file}")

    with open(before_file) as f:
        before_data = json.load(f)

    with open(after_file) as f:
        after_data = json.load(f)

    # Create comparator and detect changes
    comparator = GradeComparator()

    # Simulate the comparison with grade_changes_only=True (as used in production)
    from deepdiff import DeepDiff
    diff = DeepDiff(before_data, after_data, ignore_order=True)

    print("\n" + "="*60)
    print("DIFF SUMMARY")
    print("="*60)
    print(f"Values changed: {len(diff.get('values_changed', {}))}")
    print(f"Items added (dict): {len(diff.get('dictionary_item_added', set()))}")
    print(f"Items added (list): {len(diff.get('iterable_item_added', set()))}")

    # Process changes with grade_changes_only=True
    changes = comparator._process_changes(diff, before_data, after_data, grade_changes_only=True)

    print("\n" + "="*60)
    print("DETECTED CHANGES (grade_changes_only=True)")
    print("="*60)
    print(f"Summary: {changes['summary']}")
    print(f"Detailed changes count: {len(changes['detailed_changes'])}")

    # Check if Bedouin Presentation is in the detailed changes
    bedouin_found = False
    for change in changes['detailed_changes']:
        print(f"\nChange type: {change['type']}")
        print(f"Path: {change['path']}")

        if change['type'] == 'new_graded_assignment':
            assignment = change['assignment_data']
            print(f"  Title: {assignment.get('title')}")
            print(f"  Grade: {assignment.get('grade')}")
            print(f"  Comment: {assignment.get('comment')}")
            print(f"  Due date: {assignment.get('due_date')}")

            if 'Bedouin' in assignment.get('title', ''):
                bedouin_found = True
                print("\n✅ BEDOUIN PRESENTATION DETECTED!")

    # Format the notification message
    print("\n" + "="*60)
    print("NOTIFICATION MESSAGE")
    print("="*60)
    formatted_msg = comparator.format_changes_for_notification(changes)
    print(formatted_msg)

    print("\n" + "="*60)
    print("RESULT")
    print("="*60)
    if bedouin_found:
        print("✅ SUCCESS: Bedouin Presentation would be detected and reported!")
        return True
    else:
        print("❌ FAILURE: Bedouin Presentation NOT detected")
        return False

if __name__ == '__main__':
    success = test_bedouin_detection()
    sys.exit(0 if success else 1)
