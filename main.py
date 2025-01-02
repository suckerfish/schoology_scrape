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
# Get all courses data
print("\nGetting all courses data...")
all_courses_data = sch_driver.get_all_courses_data()

if all_courses_data:
  with open('all_courses_data.json', 'w') as f:
    json.dump(all_courses_data, f, indent=4)
else:
  print("Failed to get course data")

sch_driver.close()

