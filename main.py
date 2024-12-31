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
# Test the math course expansion
print("\nTesting math course expansion...")
success = sch_driver.test_math_expansion()

if success:
    print("Successfully expanded math course and found test assignment!")
else:
    print("Failed to expand math course properly")

sch_driver.close()