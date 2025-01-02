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
        
    def get_all_courses_data(self):
      """
        Gets data for ALL courses using dynamic class-based selectors with debug info
        """
      try:
          print("\nStarting all course data extraction...")
          self.driver.get('https://lvjusd.schoology.com/grades/grades')
          time.sleep(5)
          html = self.driver.page_source
          soup = BeautifulSoup(html, 'lxml')
          tree = etree.HTML(str(soup))


          # 1. Find courses
          print("Looking for courses...")
          courses = tree.xpath("//div[contains(@class, 'gradebook-course')]")
          print(f"Found {len(courses)} total courses")

          all_course_data = []
          for course in courses:
                course_data = {"assignments": []}
                
                # 2. Get course title and course grade
                try:
                  title_element = course.xpath(".//div[@class='gradebook-course-title']/a/span[1]/text()")[0]
                  course_data["course_name"] = title_element.strip()
                except:
                  course_data["course_name"] = "could not find title"
                
                try:
                   course_grade = course.xpath(".//div[@class='summary-course']//span[contains(@class, 'grade-value')]//text()")[0]
                   course_data["course_grade"] = course_grade.strip()
                except:
                  course_data["course_grade"] = "Not graded"

                print(f"\nProcessing course: {course_data['course_name']}")

                # 3. Get all report rows, periods, and categories for the current course.
                report_rows = course.xpath(".//tr[contains(@class, 'report-row')]")
                for row in report_rows:
                    if 'period-row' in row.get('class'):
                        period_data = {"categories": []}

                        try:
                            title_elem = row.xpath(".//span[@class='title']/text()")[0]
                            if "(no grading period)" in title_elem:
                                  continue
                            period_data["period_name"] = title_elem.strip()
                        except:
                             period_data["period_name"] = "could not find period title"

                        print(f"  Processing period: {period_data['period_name']}")

                        categories = course.xpath(".//tr[contains(@class, 'category-row') and @data-parent-id=$period_id]", period_id = row.get('data-id'))
                        for category in categories:
                                  category_data = {"assignments": []}
                                  try:
                                       category_title = category.xpath(".//span[@class='title']/text()")[0]
                                       try:
                                          weight = category.xpath(".//span[@class='percentage-contrib']/text()")[0]
                                          category_data["category_name"] = f"{category_title.strip()} {weight.strip()}"
                                       except:
                                           category_data["category_name"] = category_title.strip()
                                  except:
                                       category_data["category_name"] = "could not find category title"

                                  print(f"    Processing category: {category_data['category_name']}")

                                  assignments = course.xpath(".//tr[contains(@class, 'item-row') and @data-parent-id=$category_id]", category_id = category.get('data-id'))

                                  for assignment in assignments:
                                    try:
                                        assignment_data = {}
                                        title = assignment.xpath(".//a/text()")[0].strip()
                                        assignment_data["title"] = title

                                        try:
                                            grade = assignment.xpath(".//span[@class='rounded-grade']/text()")[0]
                                            max_grade = assignment.xpath(".//span[@class='max-grade']/text()")[0]
                                            assignment_data["grade"] = f"{grade}{max_grade}"
                                        except IndexError:
                                            assignment_data["grade"] = assignment.xpath(".//div[@class='td-content-wrapper']/text()")[0].strip()
                                            
                                        try:
                                            comment = assignment.xpath(".//div[@class='td-content-wrapper']/span[@class='comment']/text()")[0].strip()
                                            assignment_data["comment"] = comment
                                        except:
                                            assignment_data["comment"] = "No comment"

                                        print(f"        📝 {assignment_data['title']}: {assignment_data['grade']} comment: {assignment_data.get('comment')}")
                                        category_data["assignments"].append(assignment_data)

                                    except Exception as e:
                                        print(f"      Error processing assignment: {str(e)}")
                                        continue
                                  period_data["categories"].append(category_data)
                        course_data["assignments"].append(period_data)
                all_course_data.append(course_data)
          print("\nFinished all course data extraction.")
          return all_course_data
      except Exception as e:
          print(f"Error in get_all_courses_data: {str(e)}")
          return None