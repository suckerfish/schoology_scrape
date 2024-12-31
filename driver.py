import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
import time
import os
from bs4 import BeautifulSoup


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
    def test_math_expansion(self):
        """
        Test method to verify we can expand the math course and find a specific assignment
        """
        try:
            # Navigate to grades
            self.driver.get('https://lvjusd.schoology.com/grades/grades')
            time.sleep(5)  # Wait for grades page to load

            # Find and expand math course
            math_title = self.wait.until(ec.presence_of_element_located(
                (By.XPATH, "//div[contains(@class, 'gradebook-course-title')]//a[contains(text(), 'Accelerated Math')]")))
            
            # Scroll the math title into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", math_title)
            time.sleep(1)  # Wait for scroll
            
            # Click the arrow using JavaScript
            arrow = math_title.find_element(By.CLASS_NAME, "arrow")
            self.driver.execute_script("arguments[0].click();", arrow)
            time.sleep(2)

            # Find T1 element and ensure it's visible
            t1_element = self.wait.until(ec.presence_of_element_located(
                (By.XPATH, "//span[contains(@class, 'title') and contains(text(), '2024-2025 T1')]/parent::div")))
            self.driver.execute_script("arguments[0].scrollIntoView(true);", t1_element)
            time.sleep(1)
            
            # Find and click the expand icon using JavaScript
            expand_icon = t1_element.find_element(By.CLASS_NAME, "expandable-icon-grading-report")
            self.driver.execute_script("arguments[0].click();", expand_icon)
            time.sleep(2)

            # Find Classwork section and ensure it's visible
            classwork_element = self.wait.until(ec.presence_of_element_located(
                (By.XPATH, "//span[contains(@class, 'title') and text()='Classwork']/parent::div")))
            self.driver.execute_script("arguments[0].scrollIntoView(true);", classwork_element)
            time.sleep(1)
            
            # Click the classwork expand icon using JavaScript
            classwork_expand = classwork_element.find_element(By.CLASS_NAME, "expandable-icon-grading-report")
            self.driver.execute_script("arguments[0].click();", classwork_expand)
            time.sleep(2)

            # Look for our test assignment
            test_assignment = self.wait.until(ec.presence_of_element_located(
                (By.XPATH, "//a[contains(text(), '1.3 order of operation')]")))
            
            print("Found test assignment! Expansion successful!")
            
            # Get its grade using a more precise XPath
            assignment_row = test_assignment.find_element(By.XPATH, "./ancestor::tr[contains(@class, 'report-row item-row')]")
            grade_cell = assignment_row.find_element(By.CLASS_NAME, "grade-column")
            grade = grade_cell.find_element(By.CLASS_NAME, "rounded-grade").text
            max_grade = grade_cell.find_element(By.CLASS_NAME, "max-grade").text
            
            print(f"Grade: {grade}{max_grade}")
            return True

        except Exception as e:
            print(f"Error in test_math_expansion: {str(e)}")
            return False