#!/usr/bin/env python3
"""
Test script to demonstrate the new diff logging functionality.
Shows how changes are logged to separate files in structured format.
"""

import json
from pathlib import Path
from pipeline.comparator import GradeComparator
from shared.diff_logger import DiffLogger
from shared.config import get_config

def create_sample_data():
    """Create sample grade data for testing."""
    return {
        "Math 7": {
            "course_grade": "A-",
            "periods": {
                "2025-2026 T1": {
                    "period_grade": "90%",
                    "categories": {
                        "Tests (60%)": {
                            "assignments": [
                                {
                                    "title": "Chapter 1 Test",
                                    "grade": "85 / 100 / 100",
                                    "due_date": "9/10/25",
                                    "comment": "Good work!"
                                }
                            ]
                        },
                        "Homework (40%)": {
                            "assignments": [
                                {
                                    "title": "Problem Set 1",
                                    "grade": "95 / 100 / 100",
                                    "due_date": "9/5/25",
                                    "comment": "Excellent"
                                }
                            ]
                        }
                    }
                }
            }
        }
    }

def create_modified_data():
    """Create modified grade data to show changes."""
    data = create_sample_data()

    # Modify an existing grade
    data["Math 7"]["periods"]["2025-2026 T1"]["categories"]["Tests (60%)"]["assignments"][0]["grade"] = "88 / 100 / 100"

    # Add a new assignment
    data["Math 7"]["periods"]["2025-2026 T1"]["categories"]["Homework (40%)"]["assignments"].append({
        "title": "Problem Set 2",
        "grade": "92 / 100 / 100",
        "due_date": "9/12/25",
        "comment": "Nice work"
    })

    # Update period grade
    data["Math 7"]["periods"]["2025-2026 T1"]["period_grade"] = "91%"

    return data

def main():
    """Test the diff logging functionality."""
    print("🧪 Testing Diff Logging Functionality")
    print("=====================================")

    try:
        # Initialize components
        config = get_config()
        comparator = GradeComparator()
        diff_logger = DiffLogger(config)

        print(f"✅ Initialized components")
        print(f"   Change logging: {'enabled' if config.logging.enable_change_logging else 'disabled'}")
        print(f"   Raw diff logging: {'enabled' if config.logging.enable_raw_diff_logging else 'disabled'}")

        # Create test data
        old_data = create_sample_data()
        new_data = create_modified_data()

        print(f"\n📊 Test Data Created")
        print(f"   Old data: {len(old_data)} courses")
        print(f"   New data: {len(new_data)} courses")

        # Detect changes using the comparator
        changes = comparator._process_changes(
            diff=comparator._perform_deep_diff(old_data, new_data),
            old_data=old_data,
            new_data=new_data
        )

        if changes:
            print(f"\n🔍 Changes Detected")
            print(f"   Type: {changes['type']}")
            print(f"   Summary: {changes['summary']}")
            print(f"   Detailed changes: {len(changes.get('detailed_changes', []))}")

            # Format the notification message
            formatted_message = comparator.format_changes_for_notification(changes)
            print(f"\n📧 Formatted Message:")
            print(formatted_message)

            # Simulate notification results
            notification_results = {
                "pushover": True,
                "email": True,
                "gemini": False  # Simulating a failure
            }

            # Log the changes (this is what happens in production)
            diff_logger.log_grade_changes(
                changes=changes,
                formatted_message=formatted_message,
                notification_results=notification_results,
                comparison_files=["test_old_data.json", "test_new_data.json"]
            )

            print(f"\n✅ Diff logging completed!")
            print(f"   Check 'logs/grade_changes.log' for structured change data")
            if config.logging.enable_raw_diff_logging:
                print(f"   Check 'logs/raw_diffs.log' for detailed diff data")

            # Show what was logged
            change_log = Path('logs/grade_changes.log')
            if change_log.exists():
                print(f"\n📄 Latest Change Log Entry:")
                with open(change_log, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        latest_entry = json.loads(lines[-1])
                        print(f"   Timestamp: {latest_entry['timestamp']}")
                        print(f"   Change type: {latest_entry['change_type']}")
                        print(f"   Summary: {latest_entry['summary']}")
                        print(f"   Priority: {latest_entry['priority']}")
                        print(f"   Notifications: {latest_entry['notification_results']}")
                        print(f"   Change count: {latest_entry['change_count']}")
        else:
            print(f"\n❌ No changes detected")

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

def _perform_deep_diff(self, old_data, new_data):
    """Helper method for testing (normally private in comparator)."""
    from deepdiff import DeepDiff
    return DeepDiff(old_data, new_data, ignore_order=True)

# Monkey patch for testing
GradeComparator._perform_deep_diff = _perform_deep_diff

if __name__ == "__main__":
    success = main()
    if success:
        print(f"\n🎉 Diff logging test completed successfully!")
        print(f"\nNext steps:")
        print(f"  1. Run the actual pipeline to see real diff logging")
        print(f"  2. Check logs/grade_changes.log for structured data")
        print(f"  3. Enable raw_diff_logging in config.toml for debug data")
    else:
        print(f"\n❌ Test failed")
        exit(1)