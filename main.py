from driver import SchoologyDriver
import os
import json
import datetime
from pathlib import Path
from deepdiff import DeepDiff
from gemini_client import Gemini


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
    latest_file = sorted(Path('data').glob('all_courses_data_*.json'))[-1] if sorted(Path('data').glob('all_courses_data_*.json')) else None
    
    if not latest_file or DeepDiff(json.load(open(latest_file)), all_courses_data):
        # Save new data
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        new_file = f'data/all_courses_data_{timestamp}.json'
        with open(new_file, 'w') as f:
            json.dump(all_courses_data, f, indent=2)
            
        # Compare with LLM if there's a previous file
        if latest_file:
            gemini = Gemini()
            prompt = """You are analyzing changes in student grades between two JSON files. The first file shows previous grades, the second shows current grades.
                    Please describe:
                    1. New assignments added
                    2. Grade changes on existing assignments
                    3. Changes in overall course grades or period grades

                    Previous grades: {previous}
                    Current grades: {current}""".format(
                        previous=json.load(open(latest_file)),
                        current=all_courses_data
                    )
            changes = gemini.ask(prompt)
            with open(f'data/changes_{timestamp}.txt', 'w') as f:
                f.write(changes)
else:
    print("Failed to get course data")

sch_driver.close()
