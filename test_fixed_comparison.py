#!/usr/bin/env python3
"""
Test the fixed comparator
"""

import json
from pathlib import Path
import sys
import os
sys.path.append(os.getcwd())

from pipeline.comparator import GradeComparator

def test_fixed_comparison():
    """Test the fixed comparator with real data"""
    print("🔍 Testing fixed comparator...")
    
    # Load new data  
    with open('debug_new_data.json', 'r') as f:
        new_data = json.load(f)
    
    # Test the comparator
    comparator = GradeComparator()
    
    try:
        changes = comparator.detect_changes_from_file(new_data)
        
        if changes:
            print(f"✅ Changes detected!")
            print(f"   Type: {changes.get('type')}")
            print(f"   Summary: {changes.get('summary')}")
            print(f"   Detailed changes: {len(changes.get('detailed_changes', []))}")
            
            # Show first few changes
            for i, change in enumerate(changes.get('detailed_changes', [])[:3]):
                print(f"   Change {i+1}: {change['type']} - {change['path']}")
            
            return True
        else:
            print("❌ No changes detected")
            return False
            
    except Exception as e:
        print(f"❌ Error in comparator: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fixed_comparison()
    if success:
        print("\n✅ Comparator is now working correctly!")
    else:
        print("\n❌ Comparator still has issues")