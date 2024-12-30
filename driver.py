import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
import time
import os


class SchoologyDriver:
    def __init__(self, download_path):
        self.download_path = download_path
        self.setup_driver()
        self.wait = WebDriverWait(self.driver, 180)  # Adjust the timeout as necessary

    def setup_driver(self):
        chrome_options = uc.ChromeOptions()
        # Add arguments to the options
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--profile-directory=Default")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--disable-plugins-discovery")
        chrome_options.add_argument("--incognito")
        self.driver = uc.Chrome(options=chrome_options)

    def login(self, url, email, password):
        self.driver.get(url)
        email_field = self.wait.until(ec.presence_of_element_located((By.ID, "identifierId")))
        email_field.send_keys(email)
        email_field.send_keys(Keys.ENTER)
        time.sleep(3)
        password_field = self.wait.until(ec.presence_of_element_located((By.NAME, "Passwd")))
        password_field.send_keys(password)
        password_field.send_keys(Keys.ENTER)
        time.sleep(6)  # Wait for the page to load

    def get_inner_html(self, class_name):
        element = self.driver.find_element(By.CLASS_NAME, class_name)
        return element.get_attribute('innerHTML')

    def take_screenshot(self, file_name):
        self.driver.save_screenshot(file_name)

    def close(self):
        self.driver.quit()    
    # Add this method to your SchoologyDriver class in driver.py
    def get_all_courses_grades(self):
        """
        Get all courses and their grade information
        """
        # Wait for the gradebook to load
        time.sleep(5)  # Adjust if needed
        
        # Find all course divs
        courses = self.driver.find_elements(By.CLASS_NAME, "gradebook-course")
        
        for course in courses:
            # Get course title
            title = course.find_element(By.CLASS_NAME, "gradebook-course-title").text
            print(f"\nFound course: {title}")
            
            # Click the course title to expand if not expanded
            try:
                expand_button = course.find_element(By.CLASS_NAME, "arrow")
                expand_button.click()
                time.sleep(1)  # Wait for expansion
                
                # Now find and click all period row expand buttons
                period_rows = course.find_elements(By.CLASS_NAME, "period-row")
                for period in period_rows:
                    try:
                        period_expand = period.find_element(By.CLASS_NAME, "expandable-icon-grading-report")
                        period_expand.click()
                        time.sleep(0.5)  # Wait for period expansion
                        
                        # Now find and click all category row expand buttons
                        category_rows = period.find_elements(By.CLASS_NAME, "category-row")
                        for category in category_rows:
                            try:
                                category_expand = category.find_element(By.CLASS_NAME, "expandable-icon-grading-report")
                                category_expand.click()
                                time.sleep(0.5)  # Wait for category expansion
                            except:
                                continue
                    except:
                        continue
            except:
                print(f"Could not expand course: {title}")

        # Give a moment for all expansions to complete
        time.sleep(2)

        # Now return all courses for processing
        return self.driver.find_elements(By.CLASS_NAME, "gradebook-course")
    # In driver.py
    def parse_assignment_grade(self, grade_element):
        """Parse grade data from a grade column element"""
        try:
            # Handle exception cases (Missing, Incomplete)
            exception = grade_element.find_elements(By.CLASS_NAME, "exception-text")
            if exception:
                max_grade = grade_element.find_element(By.CLASS_NAME, "max-grade").text.strip(" /") if grade_element.find_elements(By.CLASS_NAME, "max-grade") else None
                return {
                    "score": "0",
                    "max": max_grade,
                    "status": exception[0].text
                }
            
            # Handle normal graded assignments
            awarded_grade = grade_element.find_element(By.CLASS_NAME, "awarded-grade")
            if awarded_grade:
                # Try to get the numeric grade first
                try:
                    grade_value = awarded_grade.find_element(By.CLASS_NAME, "rounded-grade").text
                except:
                    # If no rounded-grade, use the full awarded-grade text
                    grade_value = awarded_grade.text
                    
            max_grade = grade_element.find_element(By.CLASS_NAME, "max-grade").text.strip(" /") if grade_element.find_elements(By.CLASS_NAME, "max-grade") else None
            
            return {
                "score": grade_value,
                "max": max_grade,
                "status": "Graded"
            }
        except Exception as e:
            print(f"Warning: Error parsing grade: {str(e)}")
            return {
                "score": None,
                "max": None,
                "status": "Error parsing grade"
            }
    def get_course_structure(self, course_element):
        """Get structured data for a course including all grades"""
        try:
            title = course_element.find_element(By.CLASS_NAME, "gradebook-course-title").text.strip()
        except:
            title = "Unknown Course"
                
        # Try to get overall grade in multiple ways since the structure varies
        try:
            grade_value = course_element.find_element(By.CLASS_NAME, "course-grade-value")
            overall_grade = grade_value.text.strip()
        except:
            try:
                # Try alternate location or format
                grade_wrapper = course_element.find_element(By.CLASS_NAME, "course-grade-wrapper")
                overall_grade = grade_wrapper.text.replace("Course Grade:", "").strip()
            except:
                overall_grade = "Not Available"

        course_data = {
            "title": title,
            "overall_grade": overall_grade,
            "periods": []
        }
        
        try:
            # Get grading periods
            periods = course_element.find_elements(By.CLASS_NAME, "period-row")
            for period in periods:
                try:
                    period_title = period.find_element(By.CLASS_NAME, "title").text.strip()
                    # Skip the "(no grading period)" sections
                    if "(no grading period)" in period_title:
                        continue
                    
                    period_data = {
                        "name": period_title,
                        "categories": []
                    }
                    
                    # Get categories within period
                    categories = period.find_elements(By.CLASS_NAME, "category-row")
                    for category in categories:
                        # In get_course_structure method, inside the category loop:
                        try:
                            category_title = category.find_element(By.CLASS_NAME, "title").text.strip()
                            print(f"    Found category: {category_title}")  # Add this debug line
                            try:
                                weight = category.find_element(By.CLASS_NAME, "percentage-contrib").text.strip()
                            except:
                                weight = "Weight not specified"
                                
                            category_data = {
                                "name": category_title,
                                "weight": weight,
                                "assignments": []
                            }
                            
                            # Get assignments within category
                            assignments = category.find_elements(By.CLASS_NAME, "item-row")
                            for assignment in assignments:
                                try:
                                    assignment_data = {
                                        "name": assignment.find_element(By.CLASS_NAME, "title").text.strip(),
                                        "due_date": assignment.find_element(By.CLASS_NAME, "due-date").text.strip() if assignment.find_elements(By.CLASS_NAME, "due-date") else None,
                                        "grade": self.parse_assignment_grade(assignment.find_element(By.CLASS_NAME, "grade-column"))
                                    }
                                    category_data["assignments"].append(assignment_data)
                                except Exception as e:
                                    print(f"Warning: Could not parse assignment in {title}: {str(e)}")
                                    continue
                                    
                            period_data["categories"].append(category_data)
                        except Exception as e:
                            print(f"Warning: Could not parse category in {title}: {str(e)}")
                            continue
                            
                    course_data["periods"].append(period_data)
                except Exception as e:
                    print(f"Warning: Could not parse period in {title}: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"Warning: Could not parse periods in {title}: {str(e)}")
            
        return course_data
