from driver import SchoologyDriver
import os
import json
import datetime
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
    # Save with current timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'data/all_courses_data_{timestamp}.json'
    
    with open(filename, 'w') as f:
        json.dump(all_courses_data, f, indent=2)
    print(f"\nSaved data to {filename}")
else:
    print("Failed to get course data")

sch_driver.close()
