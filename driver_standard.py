from selenium import webdriver
from selenium.webdriver.chrome.options import Options
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
        self.wait = WebDriverWait(self.driver, 180)  # Adjust the timeout as necessary

    def setup_driver(self):
        chrome_options = Options()
        # Add arguments to the options
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--profile-directory=Default")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--disable-plugins-discovery")
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36')
        self.driver = webdriver.Chrome(options=chrome_options)

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
        
    def handle_oauth_flow(self, email):
        """Handle OAuth account selection if needed when navigating to Schoology"""
        try:
            # Check if we're in OAuth flow
            current_url = self.driver.current_url
            if "oauth" in current_url and "oauthchooseaccount" in current_url:
                print("🔄 OAuth account selection detected")
                # Look for account selection
                account_button = self.wait.until(ec.element_to_be_clickable((By.XPATH, f"//div[@data-identifier='{email}']")))
                account_button.click()
                print("👤 Account selected, waiting for OAuth completion...")
                time.sleep(5)
                return True
        except Exception as e:
            print(f"OAuth handling: {e}")
        return False

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
            text = ' '.join([node.strip() for node in nodes if node.strip()]) or None
            return self.clean_text(text) if text else None
        except Exception as e:
            print(f"Error getting text content: {str(e)}")
            return None

    def clean_text(self, text):
        """Clean unwanted phrases from text"""
        if not isinstance(text, str):
            return text
        return text.replace("Note: This material is not available within Schoology", "").strip()
        
    def get_grade_text(self, element):
        try:
            # Check for missing assignment using the specific classes
            missing = element.xpath(".//span[@class='exception-text'][text()='Missing']")
            if missing:
                return "Missing"
            
            # Enhanced grade checking logic
            alpha_grade = element.xpath(".//span[@class='alpha-grade primary-grade']/text()")
            numeric_grade = element.xpath(".//span[contains(@class, 'rounded-grade')]/text()")
            
            # Enhanced awarded-grade handling for structures like "D 2"
            awarded_grade_text = element.xpath(".//span[@class='awarded-grade']/text()")
            awarded_grade_numeric = element.xpath(".//span[@class='awarded-grade']//span[contains(@class, 'rounded-grade')]/text()")
            
            # Get max grade if available (e.g., "/ 3")
            max_grade = element.xpath(".//span[@class='max-grade']/text()")
            
            grade_parts = []
            
            # Handle different grade formats
            if alpha_grade:
                grade_parts.extend([g.strip() for g in alpha_grade if g.strip()])
            elif awarded_grade_text or awarded_grade_numeric:
                # Combine awarded grade parts (e.g., "D" + "2" = "D 2")
                if awarded_grade_text:
                    grade_parts.extend([g.strip() for g in awarded_grade_text if g.strip()])
                if awarded_grade_numeric:
                    grade_parts.extend([g.strip() for g in awarded_grade_numeric if g.strip()])
            elif numeric_grade:
                grade_parts.extend([g.strip() for g in numeric_grade if g.strip()])
            
            # Add max grade if available
            if max_grade:
                grade_parts.extend([g.strip() for g in max_grade if g.strip()])
            
            grade = ' '.join(grade_parts).strip()
            return grade if grade else "Not graded"
            
        except Exception as e:
            print(f"Error getting grade text: {str(e)}")
            return "Not graded"

    def get_all_courses_data(self, email=None):
        """Gets data for ALL courses using dynamic class-based selectors"""
        try:
            print("\nStarting all course data extraction...")
            self.driver.get('https://lvjusd.schoology.com/grades/grades')
            time.sleep(5)
            
            # Handle OAuth if needed
            if email and self.handle_oauth_flow(email):
                time.sleep(5)  # Additional wait after OAuth completion
            
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
                    grade_element = course.xpath(".//div[@class='summary-course']//span[contains(@class, 'grade-value')]")
                    if grade_element:
                        course_data["course_grade"] = self.get_grade_text(grade_element[0])
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
                            grade_element = period.xpath(".//td[@class='grade-column']")[0]
                            if grade_element is not None:
                                period_data["period_grade"] = self.get_grade_text(grade_element)
                        except:
                            pass

                        print(f"  Processing period: {period_title}")

                        # Get categories for this period
                        categories = course.xpath(f".//tr[contains(@class, 'category-row') and @data-parent-id='{period.get('data-id')}']")
                        for category in categories:
                            try:
                                # Get category name with weight if available
                                category_name = self.get_text_content(category, ".//span[@class='title']/text()")
                                weight = self.get_text_content(category, ".//span[@class='percentage-contrib']/text()")
                                if weight:
                                    category_name = f"{category_name} {weight}"
                                elif category_name == "Grade":  # Special case for PE-style categories
                                    category_name = "Grade (100%)"  # Add implicit weight

                                if not category_name:
                                    continue

                                print(f"    Processing category: {category_name}")

                                # Initialize category data
                                category_data = {"assignments": []}

                                # Get category grade if available
                                try:
                                    grade_element = category.xpath(".//td[@class='grade-column']")[0]
                                    if grade_element is not None:
                                        category_data["category_grade"] = self.get_grade_text(grade_element)
                                except:
                                    category_data["category_grade"] = "Not graded"

                                # Get assignments for this category
                                assignments = course.xpath(f".//tr[contains(@class, 'item-row') and @data-parent-id='{category.get('data-id')}']")
                                for assignment in assignments:
                                    try:
                                        # Check for both regular and grade-column style assignments
                                        is_grade_column = 'is-grade-column' in assignment.get('class', '')
                                        
                                        # Use appropriate XPath based on assignment type
                                        title_xpath = ".//span[@class='title']//text()" if is_grade_column else ".//a/text() | .//span[@class='title']/text()"
                                        title = self.get_text_content(assignment, title_xpath)
                                        
                                        if not title:
                                            continue

                                        assignment_data = {"title": title.strip()}

                                        # Get grade
                                        grade_element = assignment.xpath(".//td[@class='grade-column']")[0]
                                        if grade_element is not None:
                                            grade = self.get_grade_text(grade_element)
                                            max_grade = grade_element.xpath(".//span[@class='max-grade']/text()")
                                            if max_grade:
                                                grade = f"{grade}{max_grade[0]}"
                                            assignment_data["grade"] = grade
                                        else:
                                            assignment_data["grade"] = "No grade"

                                        # Get due date if available
                                        due_date = self.get_text_content(assignment, ".//span[@class='due-date']/text()")
                                        if due_date:
                                            if due_date.startswith("Due "):
                                                due_date = due_date[4:]
                                            assignment_data["due_date"] = due_date.strip()

                                        # Get comment if available - exclude visually-hidden text
                                        comment_element = assignment.xpath(".//span[@class='comment']")
                                        if comment_element:
                                            # Get all text but exclude visually-hidden spans
                                            comment_texts = comment_element[0].xpath(".//text()[not(parent::span[@class='visually-hidden'])]")
                                            comment = ' '.join([t.strip() for t in comment_texts if t.strip()])
                                        else:
                                            comment = "No comment"
                                        assignment_data["comment"] = comment.strip() if comment.strip() else "No comment"

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

                # Add course if it has either periods or a course grade
                if course_data["periods"] or course_data["course_grade"] != "Not graded":
                    all_courses_data[course_title] = course_data

            print("\nFinished all course data extraction.")
            return all_courses_data

        except Exception as e:
            print(f"Error in get_all_courses_data: {str(e)}")
            return None