# This script scrapes schoology page for specific HTML by finding its class name/IDs and concatenates them.
# If there is a change compared to the last time it was ran, it takes a screenshot and notes that there was a change
# future changes will email or message the screenshot and include other things to check such as grades
from driver import SchoologyDriver
import os

# Set the download path, URL, and credentials
download_path = '.'
url = 'https://lvjusd.schoology.com/'
email = os.environ.get('evan_google')
password = os.environ.get('evan_google_pw')

# Initialize the driver
sch_driver = SchoologyDriver(download_path)

# Login
sch_driver.login(url, email, password)


def read_previous_html(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    return None


def write_html(file_path, html_content):
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(html_content)


previous_all_html_filename = 'previous_all_html.txt'
previous_all_html = read_previous_html(previous_all_html_filename)


# Get inner HTML for completed and to-do
current_completed_inner_html = sch_driver.get_inner_html("recently-completed-list")
current_todo_inner_html = sch_driver.get_inner_html("todo-wrapper")

# Concatenate them into a single string
all_html = current_todo_inner_html + current_completed_inner_html

if all_html != previous_all_html:
    print("Looks like there are some changes")
    sch_driver.take_screenshot('screenshot.png')
    write_html(previous_all_html_filename, all_html)
else:
    print("No changes to previous")

# Close the driver
sch_driver.close()
