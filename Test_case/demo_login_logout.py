from pathlib import Path
import os
import sys
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


DEMO_URL = "https://practicetestautomation.com/practice-test-login/"
USERNAME = os.getenv("DEMO_USERNAME", "student")
PASSWORD = os.getenv("DEMO_PASSWORD", "Password123")
TIMEOUT_SECONDS = 15


def create_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    return webdriver.Chrome(options=options)


def save_failure_screenshot(driver):
    screenshot_dir = Path(__file__).resolve().parents[1] / "Static" / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = screenshot_dir / "demo_login_logout.png"
    driver.save_screenshot(str(screenshot_path))
    print(f"Failure screenshot saved at: {screenshot_path}")


def read_login_error(driver):
    error_elements = driver.find_elements(By.ID, "error")
    if not error_elements or not error_elements[0].is_displayed():
        return ""

    return error_elements[0].text.strip()


def run_test():
    driver = create_driver()
    wait = WebDriverWait(driver, TIMEOUT_SECONDS)

    try:
        print("Opening demo login page")
        driver.get(DEMO_URL)

        print("Submitting login credentials")
        wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys(USERNAME)
        driver.find_element(By.ID, "password").send_keys(PASSWORD)
        driver.find_element(By.ID, "submit").click()

        print("Verifying successful login")
        wait.until(
            lambda current_driver: (
                "logged-in-successfully" in current_driver.current_url
                or read_login_error(current_driver)
            )
        )

        login_error = read_login_error(driver)
        if login_error:
            if "password" in login_error.lower():
                raise AssertionError("Login failed because the password is incorrect.")
            if "username" in login_error.lower():
                raise AssertionError("Login failed because the username is incorrect.")
            raise AssertionError(f"Login failed: {login_error}")

        success_heading = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//h1[contains(., 'Logged In Successfully')]"))
        )
        assert success_heading.is_displayed(), "Success heading was not displayed after login"

        print("Logging out")
        wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Log out"))).click()

        print("Verifying logout returned to login page")
        wait.until(EC.visibility_of_element_located((By.ID, "username")))
        assert "practice-test-login" in driver.current_url, "Logout did not return to the login page"

        print("Demo login/logout test passed")
        return 0

    except (AssertionError, TimeoutException, Exception) as error:
        print(f"Demo login/logout test failed: {error}")
        save_failure_screenshot(driver)
        return 1

    finally:
        time.sleep(1)
        driver.quit()


if __name__ == "__main__":
    sys.exit(run_test())
