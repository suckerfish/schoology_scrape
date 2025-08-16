#!.venv/bin/python
from driver_standard import SchoologyDriver
from dotenv import load_dotenv
import os
import json
import datetime
from pathlib import Path
from deepdiff import DeepDiff
from gemini_client import Gemini
from pushover import send_pushover_message
from email_myself import send_email_to_myself
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))
from grade_data_service import create_grade_data_service

# Load environment variables
load_dotenv()

# Set the download path, URL, and credentials
download_path = '.'
url = 'https://lvjusd.schoology.com/'
email = os.getenv('evan_google')
password = os.getenv('evan_google_pw')

# Initialize the driver
sch_driver = SchoologyDriver(download_path)

# Login
sch_driver.login(url, email, password)

# After login, navigate to grades page
# Get all courses data
print("\nGetting all courses data...")
all_courses_data = sch_driver.get_all_courses_data(email=email)

if all_courses_data:
    latest_file = sorted(Path('data').glob('all_courses_data_*.json'))[-1] if sorted(Path('data').glob('all_courses_data_*.json')) else None
    
    if not latest_file or DeepDiff(json.load(open(latest_file)), all_courses_data):
        # Save new data
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        new_file = f'data/all_courses_data_{timestamp}.json'
        with open(new_file, 'w') as f:
            json.dump(all_courses_data, f, indent=2)
            
        # Save to DynamoDB
        service = create_grade_data_service()
        service.save_snapshot(all_courses_data)

else:
    print("Failed to get course data")

sch_driver.close()
