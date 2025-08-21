#!/usr/bin/env python3
"""
Test comparison with the actual new vs old data
"""

import json
from pathlib import Path
from deepdiff import DeepDiff

def test_real_comparison():
    """Test the real comparison that's failing"""
    print("🔍 Testing real data comparison...")
    
    # Load old data
    data_dir = Path('data')
    latest_files = sorted(data_dir.glob('all_courses_data_*.json'))
    latest_file = latest_files[-1]
    
    with open(latest_file, 'r') as f:
        old_data = json.load(f)
    
    # Load new data  
    with open('debug_new_data.json', 'r') as f:
        new_data = json.load(f)
    
    print(f"📊 Old data: {len(old_data)} courses")
    print(f"📊 New data: {len(new_data)} courses") 
    print(f"🔍 Old courses: {list(old_data.keys())}")
    print(f"🔍 New courses: {list(new_data.keys())}")
    
    # Perform the comparison
    try:
        diff = DeepDiff(old_data, new_data, ignore_order=True)
        print(f"\n🔍 Diff result: {diff}")
        print(f"🔍 Diff keys: {list(diff.keys())}")
        
        # Try to process like the comparator does
        detailed_changes = []
        
        # Process value changes
        if 'values_changed' in diff:
            print(f"\n📝 Processing {len(diff['values_changed'])} value changes...")
            for path, change in diff['values_changed'].items():
                print(f"   {path}: {change['old_value']} -> {change['new_value']}")
                detailed_changes.append({
                    'type': 'value_changed',
                    'path': path,
                    'old_value': change['old_value'],
                    'new_value': change['new_value']
                })
        
        # Process additions - this is likely where the error occurs
        if 'dictionary_item_added' in diff:
            print(f"\n📝 Processing {len(diff['dictionary_item_added'])} additions...")
            print(f"   Type of dictionary_item_added: {type(diff['dictionary_item_added'])}")
            
            # Debug the structure
            for i, (path, value) in enumerate(diff['dictionary_item_added'].items()):
                print(f"   {i}: {path} = {type(value)} (first 100 chars: {str(value)[:100]})")
                
                # This is the line that might be failing
                detailed_changes.append({
                    'type': 'item_added',
                    'path': path,
                    'value': value  # This might be causing the issue
                })
                
                if i >= 5:  # Limit output
                    break
        
        # Process removals
        if 'dictionary_item_removed' in diff:
            print(f"\n📝 Processing {len(diff['dictionary_item_removed'])} removals...")
            for path, value in diff['dictionary_item_removed'].items():
                detailed_changes.append({
                    'type': 'item_removed',
                    'path': path,
                    'value': value
                })
        
        print(f"\n✅ Successfully processed {len(detailed_changes)} changes")
        
        # Generate summary like the comparator does
        summary_parts = []
        
        if 'values_changed' in diff:
            summary_parts.append(f"{len(diff['values_changed'])} value(s) changed")
        
        if 'dictionary_item_added' in diff:
            summary_parts.append(f"{len(diff['dictionary_item_added'])} item(s) added")
        
        if 'dictionary_item_removed' in diff:
            summary_parts.append(f"{len(diff['dictionary_item_removed'])} item(s) removed")
        
        summary = ", ".join(summary_parts) if summary_parts else "Unknown changes detected"
        print(f"📋 Summary: {summary}")
        
    except Exception as e:
        print(f"❌ Error in comparison: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_real_comparison()