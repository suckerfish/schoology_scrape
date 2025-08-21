#!/usr/bin/env python3
"""
Test the scraper data structure and compare with old format
"""

import json
from pathlib import Path
import sys
import os
sys.path.append(os.getcwd())

from pipeline.scraper import GradeScraper

def test_scraper_data():
    """Test what data structure the scraper is producing"""
    print("🔍 Testing scraper data structure...")
    
    # Load the latest old file for comparison
    data_dir = Path('data')
    latest_files = sorted(data_dir.glob('all_courses_data_*.json'))
    
    if latest_files:
        latest_file = latest_files[-1]
        with open(latest_file, 'r') as f:
            old_data = json.load(f)
        print(f"📁 Old data structure from {latest_file.name}:")
        print(f"   Type: {type(old_data)}")
        print(f"   Keys: {list(old_data.keys())}")
        if old_data:
            first_course = list(old_data.keys())[0]
            print(f"   First course: {first_course}")
            print(f"   Course structure: {list(old_data[first_course].keys())}")
    
    # Test what the scraper produces
    print("\n🔍 Testing scraper output...")
    
    try:
        scraper = GradeScraper()
        with scraper as s:
            new_data = s.full_scrape_session('.')
        
        print(f"📊 New data structure:")
        print(f"   Type: {type(new_data)}")
        if new_data:
            print(f"   Keys: {list(new_data.keys())}")
            first_course = list(new_data.keys())[0]
            print(f"   First course: {first_course}")
            print(f"   Course structure: {list(new_data[first_course].keys())}")
            
            # Save a sample for debugging
            with open('debug_new_data.json', 'w') as f:
                json.dump(new_data, f, indent=2)
            print(f"💾 Saved new data to debug_new_data.json")
        else:
            print("❌ Scraper returned no data")
            
    except Exception as e:
        print(f"❌ Error testing scraper: {e}")

if __name__ == "__main__":
    test_scraper_data()