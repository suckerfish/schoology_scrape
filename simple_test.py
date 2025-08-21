#!/usr/bin/env python3
"""
Simple test to check if the data files can be compared
"""

import json
from pathlib import Path

def simple_change_test():
    """Simple test of the file comparison logic"""
    print("Testing basic file comparison...")
    
    # Get the latest files
    data_dir = Path('data')
    if not data_dir.exists():
        print("❌ No data directory found")
        return False
    
    latest_files = sorted(data_dir.glob('all_courses_data_*.json'))
    if len(latest_files) < 2:
        print(f"❌ Need at least 2 files for comparison, found {len(latest_files)}")
        return False
    
    # Compare the last two files
    file1 = latest_files[-2]
    file2 = latest_files[-1]
    
    print(f"📁 Comparing {file1.name} vs {file2.name}")
    
    try:
        with open(file1, 'r') as f:
            data1 = json.load(f)
        with open(file2, 'r') as f:
            data2 = json.load(f)
        
        print(f"✅ File 1: {len(data1)} courses")
        print(f"✅ File 2: {len(data2)} courses")
        
        # Simple equality check
        if data1 == data2:
            print("🔍 Files are identical")
            return False  # This would explain no changes detected
        else:
            print("🔍 Files are different")
            
            # Count some basic differences
            diff_courses = set(data1.keys()) ^ set(data2.keys())
            if diff_courses:
                print(f"   - Course differences: {diff_courses}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error reading files: {e}")
        return False

if __name__ == "__main__":
    simple_change_test()