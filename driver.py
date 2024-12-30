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
