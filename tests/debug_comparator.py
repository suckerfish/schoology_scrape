#!/usr/bin/env python3
"""
Debug the comparator error with actual data
"""

import json
from pathlib import Path
from deepdiff import DeepDiff

def debug_comparator():
    """Debug the comparator issue"""
    print("🔍 Debugging comparator error...")
    
    # Load the latest two files
    data_dir = Path('data')
    latest_files = sorted(data_dir.glob('all_courses_data_*.json'))
    
    if len(latest_files) < 2:
        print("❌ Need at least 2 files")
        return
    
    file1 = latest_files[-2]  # Previous
    file2 = latest_files[-1]  # Latest
    
    print(f"📁 Comparing {file1.name} vs {file2.name}")
    
    try:
        with open(file1, 'r') as f:
            data1 = json.load(f)
        with open(file2, 'r') as f:
            data2 = json.load(f)
        
        print(f"✅ Loaded data: {len(data1)} vs {len(data2)} courses")
        
        # Perform the same DeepDiff operation as the comparator
        diff = DeepDiff(data1, data2, ignore_order=True)
        
        print(f"🔍 Diff keys: {list(diff.keys())}")
        
        # Check for the problematic sections
        if 'dictionary_item_added' in diff:
            print(f"📝 Items added: {len(diff['dictionary_item_added'])}")
            for i, (path, value) in enumerate(diff['dictionary_item_added'].items()):
                print(f"  {i}: {path} = {type(value)}")
                if i > 5:  # Limit output
                    break
        
        if 'values_changed' in diff:
            print(f"📝 Values changed: {len(diff['values_changed'])}")
            for i, (path, change) in enumerate(diff['values_changed'].items()):
                print(f"  {i}: {path}")
                if i > 5:  # Limit output
                    break
        
        # Try to reproduce the error
        try:
            detailed_changes = []
            
            # Process value changes
            if 'values_changed' in diff:
                for path, change in diff['values_changed'].items():
                    detailed_changes.append({
                        'type': 'value_changed',
                        'path': path,
                        'old_value': change['old_value'],
                        'new_value': change['new_value']
                    })
            
            # Process additions - this is likely where the error occurs
            if 'dictionary_item_added' in diff:
                for path in diff['dictionary_item_added']:
                    print(f"🔍 Processing added item: {path} (type: {type(path)})")
                    detailed_changes.append({
                        'type': 'item_added',
                        'path': path,
                        'value': diff['dictionary_item_added'][path]
                    })
            
            print(f"✅ Processed {len(detailed_changes)} changes successfully")
            
        except Exception as e:
            print(f"❌ Error in processing: {e}")
            print(f"   Error type: {type(e)}")
            
            # Debug the specific error
            if 'dictionary_item_added' in diff:
                print(f"🔍 Debug dictionary_item_added:")
                print(f"   Type: {type(diff['dictionary_item_added'])}")
                for i, item in enumerate(diff['dictionary_item_added']):
                    print(f"   Item {i}: {item} (type: {type(item)})")
                    if i > 3:
                        break
        
    except Exception as e:
        print(f"❌ Error loading files: {e}")

if __name__ == "__main__":
    debug_comparator()