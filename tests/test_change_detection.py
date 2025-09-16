#!/usr/bin/env python3
"""
Quick test script to debug change detection issues
"""

import json
from pathlib import Path
from pipeline.comparator import GradeComparator

def test_file_based_comparison():
    """Test the file-based comparison logic"""
    print("Testing file-based change detection...")
    
    # Initialize comparator
    comparator = GradeComparator()
    
    # Get the latest file
    data_dir = Path('data')
    if not data_dir.exists():
        print("❌ No data directory found")
        return False
    
    latest_files = sorted(data_dir.glob('all_courses_data_*.json'))
    if not latest_files:
        print("❌ No data files found")
        return False
    
    latest_file = latest_files[-1]
    print(f"📁 Latest file: {latest_file}")
    
    # Load the latest file data
    try:
        with open(latest_file, 'r') as f:
            latest_data = json.load(f)
        print(f"✅ Successfully loaded latest data with {len(latest_data)} courses")
    except Exception as e:
        print(f"❌ Error loading latest file: {e}")
        return False
    
    # Test 1: Compare identical data (should return None - no changes)
    print("\n🧪 Test 1: Comparing identical data...")
    changes = comparator.detect_changes_from_file(latest_data)
    if changes is None:
        print("✅ Correctly detected no changes for identical data")
    else:
        print(f"❌ Unexpected changes detected for identical data: {changes}")
        return False
    
    # Test 2: Compare with modified data (should detect changes)
    print("\n🧪 Test 2: Comparing with modified data...")
    modified_data = latest_data.copy()
    
    # Add a small change
    if modified_data:
        first_course = list(modified_data.keys())[0]
        if 'periods' in modified_data[first_course]:
            first_period = list(modified_data[first_course]['periods'].keys())[0]
            # Add a test assignment
            if 'categories' in modified_data[first_course]['periods'][first_period]:
                first_category = list(modified_data[first_course]['periods'][first_period]['categories'].keys())[0]
                test_assignment = {
                    "assignment_name": "TEST_ASSIGNMENT_FOR_DETECTION",
                    "grade": "100",
                    "points_earned": "100", 
                    "points_possible": "100",
                    "due_date": "Test Date",
                    "comments": "Test assignment for change detection"
                }
                modified_data[first_course]['periods'][first_period]['categories'][first_category]['assignments'].append(test_assignment)
                print(f"✏️  Added test assignment to {first_course} > {first_period} > {first_category}")
    
    changes = comparator.detect_changes_from_file(modified_data)
    if changes is not None:
        print(f"✅ Correctly detected changes: {changes.get('summary', 'Unknown changes')}")
        return True
    else:
        print("❌ Failed to detect changes in modified data")
        return False

if __name__ == "__main__":
    print("🔍 Testing change detection logic...\n")
    success = test_file_based_comparison()
    
    if success:
        print("\n✅ Change detection appears to be working correctly")
        print("🔍 The issue might be elsewhere in the pipeline...")
    else:
        print("\n❌ Change detection has issues that need to be fixed")