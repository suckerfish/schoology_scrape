# This script scrapes schoology page for specific HTML by finding its class name/IDs and concatenates them.
# If there is a change compared to the last time it was ran, it takes a screenshot and notes that there was a change
# future changes will email or message the screenshot and include other things to check such as grades
from driver import SchoologyDriver
import os
import json
import datetime
import difflib
from pathlib import Path

# Set the download path, URL, and credentials
download_path = '.'
url = 'https://lvjusd.schoology.com/'
email = os.environ.get('evan_google')
password = os.environ.get('evan_google_pw')

# Initialize the driver
sch_driver = SchoologyDriver(download_path)

# Login
sch_driver.login(url, email, password)

# After login, navigate to grades page
print("\nNavigating to grades page...")
sch_driver.driver.get('https://lvjusd.schoology.com/grades/grades')

# Wait for the page to load
import time
time.sleep(5)  # Give extra time for the page to fully load

# Get all courses and expand their grade sections
print("\nExpanding grade sections...")
courses = sch_driver.get_all_courses_grades()
time.sleep(2)  # Wait for expansions to complete
    
print("\nExtracting grade data...")
courses_data = []
for course in courses:
    try:
        course_data = sch_driver.get_course_structure(course)
        if course_data["title"] != "Unknown Course":  # Skip any malformed courses
            courses_data.append(course_data)
            print(f"\nProcessed course: {course_data['title']}")
            # Print some debug info about what we found
            for period in course_data.get("periods", []):
                print(f"  Period: {period['name']}")
                for category in period.get("categories", []):
                    print(f"    Category: {category['name']} ({category['weight']})")
                    print(f"    Found {len(category.get('assignments', []))} assignments")
    except Exception as e:
        print(f"Error processing course: {str(e)}")
        continue

def save_grade_snapshot(courses_data):
    """Save the current grades to a JSON file"""
    filename = "grades_dump.json"
    
    with open(filename, 'w') as f:
        json.dump(courses_data, f, indent=2, default=str)
    
    return filename
        
# Save new snapshot
print("\nSaving data to JSON...")
save_grade_snapshot(courses_data)
        
sch_driver.close()