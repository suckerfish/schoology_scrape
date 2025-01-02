import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
import time
import os
from bs4 import BeautifulSoup
from lxml import etree
import json


class SchoologyDriver:
    def __init__(self, download_path):
        self.download_path = download_path
        self.setup_driver()
        self.wait = WebDriverWait(self.driver, 180)

    def setup_driver(self):
        chrome_options = uc.ChromeOptions()
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
        time.sleep(6)

    def get_inner_html(self, class_name):
        element = self.driver.find_element(By.CLASS_NAME, class_name)
        return element.get_attribute('innerHTML')

    def take_screenshot(self, file_name):
        self.driver.save_screenshot(file_name)

    def close(self):
        self.driver.quit()

    def get_text_content(self, element, xpath):
        """Helper method to safely get text content"""
        try:
            nodes = element.xpath(xpath)
            if not nodes:
                return None
            # Combine all text nodes and strip whitespace
            return ' '.join([node.strip() for node in nodes if node.strip()]) or None
        except Exception as e:
            print(f"Error getting text content: {str(e)}")
            return None

    def get_all_courses_data(self):
        """Gets data for ALL courses using dynamic class-based selectors"""
        try:
            print("\nStarting all course data extraction...")
            self.driver.get('https://lvjusd.schoology.com/grades/grades')
            time.sleep(5)
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'lxml')
            tree = etree.HTML(str(soup))

            # Find all course containers
            print("Looking for courses...")
            courses = tree.xpath("//div[contains(@class, 'gradebook-course')]")
            print(f"Found {len(courses)} total courses")

            all_courses_data = {}

            for course in courses:
                # Get course title - combining text nodes and handling structure better
                course_title_nodes = course.xpath(".//div[@class='gradebook-course-title']//text()[not(parent::span[@class='visually-hidden']) and not(parent::span[@class='arrow'])]")
                course_title = ' '.join(node.strip() for node in course_title_nodes if node.strip())
                
                if not course_title:
                    print("Warning: Could not find course title, skipping...")
                    continue

                print(f"\nProcessing course: {course_title}")
                
                # Initialize course data structure
                course_data = {
                    "course_grade": "Not graded",
                    "periods": {}
                }

                # Get overall course grade if available
                try:
                    grade_element = course.xpath(".//div[@class='summary-course']//span[contains(@class, 'grade-value')]//text()")
                    if grade_element:
                        course_data["course_grade"] = grade_element[0].strip()
                except Exception as e:
                    print(f"Error getting course grade: {str(e)}")

                # Process all grading periods
                periods = course.xpath(".//tr[contains(@class, 'period-row')]")
                for period in periods:
                    try:
                        period_title = self.get_text_content(period, ".//span[@class='title']/text()")
                        if not period_title or "(no grading period)" in period_title:
                            continue

                        # Initialize period data
                        period_data = {
                            "period_grade": "Not graded",
                            "categories": {}
                        }

                        # Get period grade if available 
                        try:
                            grade_texts = period.xpath(".//td[@class='grade-column']//span[@class='awarded-grade']//text()")
                            if grade_texts:
                                period_data["period_grade"] = ''.join(text.strip() for text in grade_texts if text.strip())
                            if not period_data["period_grade"]:
                                period_data["period_grade"] = "Not graded"
                        except Exception as e:
                            print(f"    Error getting period grade: {str(e)}")
                            period_data["period_grade"] = "Not graded"

                        print(f"  Processing period: {period_title}")

                        # Get categories for this period
                        categories = course.xpath(f".//tr[contains(@class, 'category-row') and @data-parent-id='{period.get('data-id')}']")
                        for category in categories:
                            try:
                                # Get category name - handle both weighted and unweighted cases
                                category_name = self.get_text_content(category, ".//span[@class='title']/text()")
                                weight = self.get_text_content(category, ".//span[@class='percentage-contrib']/text()")
                                if weight:
                                    category_name = f"{category_name} {weight}"
                                elif category_name == "Grade":  # Special case for PE-style categories
                                    category_name = "Grade (100%)"  # Add implicit weight

                                if not category_name:
                                    continue

                                print(f"    Processing category: {category_name}")

                                category_data = {"assignments": []}

                                # Get assignments for this category
                                assignments = course.xpath(f".//tr[contains(@class, 'item-row') and @data-parent-id='{category.get('data-id')}']")
                                for assignment in assignments:
                                    try:
                                        # Try multiple XPaths for assignment title
                                        title = (
                                            self.get_text_content(assignment, ".//a/text()") or
                                            self.get_text_content(assignment, ".//span[@class='title']/text()")
                                        )
                                        if not title:
                                            continue

                                        assignment_data = {"title": title.strip()}

                                        # Get grade
                                        earned = self.get_text_content(assignment, ".//span[@class='rounded-grade']/text()")
                                        total = self.get_text_content(assignment, ".//span[@class='max-grade']/text()")
                                        if earned and total:
                                            assignment_data["grade"] = f"{earned.strip()}{total.strip()}"
                                        else:
                                            # Try alternate grade formats
                                            grade_text = (
                                                self.get_text_content(assignment, ".//div[@class='td-content-wrapper']/text()") or
                                                "No grade"
                                            )
                                            assignment_data["grade"] = grade_text.strip()

                                        # Get due date if available
                                        due_date = self.get_text_content(assignment, ".//span[@class='due-date']/text()")
                                        if due_date:
                                            if due_date.startswith("Due "):
                                                due_date = due_date[4:]
                                            assignment_data["due_date"] = due_date.strip()

                                        # Get comment if available
                                        comment = (
                                            self.get_text_content(assignment, ".//span[@class='comment']/text()") or
                                            "No comment"
                                        )
                                        assignment_data["comment"] = comment.strip()

                                        print(f"        📝 {title}: {assignment_data['grade']}")
                                        category_data["assignments"].append(assignment_data)

                                    except Exception as e:
                                        print(f"      Error processing assignment: {str(e)}")
                                        continue

                                if category_data["assignments"]:  # Only add if there are assignments
                                    period_data["categories"][category_name] = category_data

                            except Exception as e:
                                print(f"    Error processing category: {str(e)}")
                                continue

                        if period_data["categories"]:  # Only add if there are categories
                            course_data["periods"][period_title] = period_data

                    except Exception as e:
                        print(f"  Error processing period: {str(e)}")
                        continue

                if course_data["periods"]:  # Only add if there are periods
                    all_courses_data[course_title] = course_data

            print("\nFinished all course data extraction.")
            return all_courses_data

        except Exception as e:
            print(f"Error in get_all_courses_data: {str(e)}")
            return None