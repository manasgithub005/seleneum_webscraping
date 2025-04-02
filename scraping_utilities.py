import random
import time
import requests
import json
import os
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from loguru import logger
from tqdm import tqdm

class ScrapingUtilities:
    def __init__(self):
        """Initialize the ScrapingUtilities class"""
        self.ua = UserAgent()
        self.proxies = []
        self.current_proxy_index = 0
        
    def get_random_user_agent(self):
        """Get a random user agent string"""
        return self.ua.random
    
    def get_proxy_list(self, api_key=None, free_proxies=True):
        """
        Get a list of proxies
        
        Args:
            api_key (str, optional): API key for proxy service
            free_proxies (bool): Whether to use free proxies if no API key is provided
            
        Returns:
            list: List of proxy addresses
        """
        # Use paid proxy service if API key is provided
        if api_key:
            try:
                # Example with proxy service (replace with actual service endpoint)
                response = requests.get(
                    f"https://example-proxy-service.com/api/v1/proxies?api_key={api_key}"
                )
                if response.status_code == 200:
                    data = response.json()
                    self.proxies = [f"{p['ip']}:{p['port']}" for p in data.get('proxies', [])]
                    logger.info(f"Loaded {len(self.proxies)} proxies from paid service")
                    return self.proxies
                else:
                    logger.error(f"Failed to fetch proxies: {response.status_code}")
            except Exception as e:
                logger.error(f"Error fetching proxies from API: {e}")
        
        # Fall back to free proxies if enabled
        if free_proxies:
            try:
                # Free proxy list (example)
                response = requests.get("https://www.sslproxies.org/")
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                proxy_list = []
                for row in soup.select("table#proxylisttable tr"):
                    cells = row.find_all("td")
                    if len(cells) > 1:
                        ip = cells[0].text
                        port = cells[1].text
                        proxy_list.append(f"{ip}:{port}")
                
                # Test proxies before returning
                working_proxies = self.test_proxies(proxy_list)
                self.proxies = working_proxies
                logger.info(f"Loaded {len(self.proxies)} working free proxies")
                return self.proxies
            except Exception as e:
                logger.error(f"Error fetching free proxies: {e}")
        
        logger.warning("No proxies loaded. Continuing without proxies.")
        return []
    
    def test_proxies(self, proxy_list, test_url="https://www.google.com", timeout=5, max_test=20):
        """
        Test proxies to find working ones
        
        Args:
            proxy_list (list): List of proxies to test
            test_url (str): URL to test proxies against
            timeout (int): Request timeout in seconds
            max_test (int): Maximum number of proxies to test
            
        Returns:
            list: List of working proxies
        """
        working_proxies = []
        
        # Limit the number of proxies to test
        test_proxies = proxy_list[:min(len(proxy_list), max_test)]
        
        logger.info(f"Testing {len(test_proxies)} proxies")
        for proxy in tqdm(test_proxies, desc="Testing proxies"):
            try:
                response = requests.get(
                    test_url,
                    proxies={"http": f"http://{proxy}", "https": f"https://{proxy}"},
                    timeout=timeout,
                    headers={"User-Agent": self.get_random_user_agent()}
                )
                if response.status_code == 200:
                    working_proxies.append(proxy)
                    logger.debug(f"Proxy {proxy} is working")
            except:
                continue
        
        return working_proxies
    
    def get_next_proxy(self):
        """Get the next proxy in rotation"""
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        return proxy
    
    def add_proxy_to_driver(self, chrome_options, proxy=None):
        """
        Add proxy to Chrome webdriver options
        
        Args:
            chrome_options (selenium.webdriver.chrome.options.Options): Chrome options
            proxy (str, optional): Specific proxy to use, otherwise uses next in rotation
            
        Returns:
            selenium.webdriver.chrome.options.Options: Updated Chrome options
        """
        if proxy is None:
            proxy = self.get_next_proxy()
        
        if proxy:
            chrome_options.add_argument(f'--proxy-server={proxy}')
            logger.info(f"Using proxy: {proxy}")
        
        return chrome_options
    
    def handle_captcha(self, driver, timeout=30, captcha_iframe_selector=None, manual_intervention=True):
        """
        Handle CAPTCHA challenges
        
        Args:
            driver (selenium.webdriver.Chrome): Chrome webdriver
            timeout (int): Maximum time to wait for CAPTCHA resolution in seconds
            captcha_iframe_selector (str, optional): CSS selector for CAPTCHA iframe
            manual_intervention (bool): Whether to allow manual intervention
            
        Returns:
            bool: True if CAPTCHA was successfully handled, False otherwise
        """
        # Check for common CAPTCHA indicators
        captcha_indicators = [
            "//iframe[contains(@src, 'recaptcha')]",
            "//iframe[contains(@src, 'hcaptcha')]",
            "//div[contains(@class, 'g-recaptcha')]",
            "//div[contains(@class, 'h-captcha')]",
            "//input[@id='captcha']"
        ]
        
        if captcha_iframe_selector:
            captcha_indicators.append(f"//{captcha_iframe_selector}")
        
        captcha_detected = False
        for indicator in captcha_indicators:
            try:
                if driver.find_elements(By.XPATH, indicator):
                    captcha_detected = True
                    break
            except:
                continue
        
        if not captcha_detected:
            return True  # No CAPTCHA detected
        
        logger.warning("CAPTCHA detected")
        
        if manual_intervention:
            # Alert the user and wait for manual intervention
            print("\n" + "="*50)
            print("CAPTCHA DETECTED! Please solve the CAPTCHA in the browser window.")
            print("The script will continue automatically after the CAPTCHA is solved.")
            print("="*50 + "\n")
            
            # Wait for CAPTCHA to be solved (checking if the indicators disappear)
            start_time = time.time()
            while time.time() - start_time < timeout:
                all_gone = True
                for indicator in captcha_indicators:
                    try:
                        if driver.find_elements(By.XPATH, indicator):
                            all_gone = False
                            break
                    except:
                        continue
                
                if all_gone:
                    logger.info("CAPTCHA appears to be solved")
                    time.sleep(2)  # Give a little extra time for page to load
                    return True
                
                time.sleep(1)
            
            logger.error("CAPTCHA not solved within timeout period")
            return False
        else:
            # Automated CAPTCHA solving would go here (requires external services)
            logger.error("Automated CAPTCHA solving not implemented")
            return False
    
    def implement_retry_mechanism(self, function, max_retries=3, backoff_factor=2, initial_wait=1,
                                 error_types=(Exception,), retry_on_captcha=True):
        """
        Retry mechanism for web scraping functions
        
        Args:
            function (callable): Function to retry
            max_retries (int): Maximum number of retry attempts
            backoff_factor (int): Factor to increase wait time between retries
            initial_wait (int): Initial wait time in seconds
            error_types (tuple): Exception types to catch and retry
            retry_on_captcha (bool): Whether to retry on CAPTCHA detection
            
        Returns:
            callable: Wrapped function with retry logic
        """
        def wrapper(*args, **kwargs):
            retries = 0
            wait_time = initial_wait
            
            while retries <= max_retries:
                try:
                    result = function(*args, **kwargs)
                    
                    # Check if result is a CAPTCHA page (if function returns a driver)
                    if retry_on_captcha and hasattr(result, 'page_source'):
                        captcha_indicators = ['recaptcha', 'hcaptcha', 'captcha']
                        if any(indicator in result.page_source.lower() for indicator in captcha_indicators):
                            if self.handle_captcha(result):
                                return function(*args, **kwargs)  # Try again after CAPTCHA
                            else:
                                retries += 1
                                wait_time *= backoff_factor
                                logger.warning(f"CAPTCHA handling failed, retrying ({retries}/{max_retries})")
                                time.sleep(wait_time)
                                continue
                    
                    return result  # Success
                except error_types as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Failed after {max_retries} retries: {e}")
                        raise
                    
                    logger.warning(f"Attempt {retries}/{max_retries} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    wait_time *= backoff_factor
            
            raise Exception(f"Failed after {max_retries} retries")
        
        return wrapper
    
    def random_sleep(self, min_seconds=1, max_seconds=5):
        """
        Sleep for a random amount of time
        
        Args:
            min_seconds (float): Minimum sleep time in seconds
            max_seconds (float): Maximum sleep time in seconds
        """
        sleep_time = random.uniform(min_seconds, max_seconds)
        time.sleep(sleep_time)
    
    def add_anti_bot_measures(self, driver):
        """
        Add anti-bot measures to a webdriver
        
        Args:
            driver (selenium.webdriver.Chrome): Chrome webdriver
            
        Returns:
            selenium.webdriver.Chrome: Modified webdriver
        """
        # Mask WebDriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Add random user language
        languages = ['en-US', 'en-GB', 'fr-FR', 'de-DE', 'es-ES', 'it-IT']
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": self.get_random_user_agent(),
            "acceptLanguage": random.choice(languages)
        })
        
        # Add random screen dimensions
        widths = [1366, 1440, 1536, 1600, 1920, 2048, 2560]
        heights = [768, 900, 1024, 1050, 1080, 1200, 1440]
        width = random.choice(widths)
        height = random.choice(heights)
        driver.set_window_size(width, height)
        
        return driver
    
    def is_blocked(self, driver, block_indicators=None):
        """
        Check if the website has blocked the scraper
        
        Args:
            driver (selenium.webdriver.Chrome): Chrome webdriver
            block_indicators (list): Custom block indicators
            
        Returns:
            bool: True if blocked, False otherwise
        """
        default_indicators = [
            "captcha",
            "security check",
            "access denied",
            "blocked",
            "rate limit",
            "too many requests",
            "unusual activity",
            "suspicious activity",
            "detected unusual traffic"
        ]
        
        indicators = default_indicators
        if block_indicators:
            indicators.extend(block_indicators)
        
        page_source = driver.page_source.lower()
        for indicator in indicators:
            if indicator in page_source:
                logger.warning(f"Block detected: '{indicator}' found on page")
                return True
        
        # Also check HTTP status (if available)
        try:
            response_code = driver.execute_script("return window.performance.getEntries()[0].responseStatus")
            if response_code in [403, 429]:
                logger.warning(f"Block detected: HTTP {response_code}")
                return True
        except:
            pass
        
        return False
    
    def save_cookies(self, driver, cookie_file="cookies.json"):
        """
        Save cookies from the webdriver
        
        Args:
            driver (selenium.webdriver.Chrome): Chrome webdriver
            cookie_file (str): Path to save cookies
        """
        try:
            cookies = driver.get_cookies()
            with open(cookie_file, 'w') as f:
                json.dump(cookies, f)
            logger.info(f"Saved {len(cookies)} cookies to {cookie_file}")
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
    
    def load_cookies(self, driver, cookie_file="cookies.json"):
        """
        Load cookies into the webdriver
        
        Args:
            driver (selenium.webdriver.Chrome): Chrome webdriver
            cookie_file (str): Path to load cookies from
            
        Returns:
            bool: True if cookies were loaded successfully, False otherwise
        """
        if not os.path.exists(cookie_file):
            logger.warning(f"Cookie file {cookie_file} not found")
            return False
        
        try:
            with open(cookie_file, 'r') as f:
                cookies = json.load(f)
            
            for cookie in cookies:
                # Some cookies cannot be loaded as is
                if 'expiry' in cookie:
                    cookie['expiry'] = int(cookie['expiry'])
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    logger.debug(f"Failed to add cookie {cookie.get('name')}: {e}")
            
            logger.info(f"Loaded {len(cookies)} cookies from {cookie_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return False

# Example usage if this script is run directly
if __name__ == "__main__":
    # Configure logger
    logger.add("scraping_utilities.log", rotation="10 MB")
    
    # Create an instance of ScrapingUtilities
    utils = ScrapingUtilities()
    
    # Test getting a random user agent
    user_agent = utils.get_random_user_agent()
    print(f"Random User Agent: {user_agent}")
    
    # Test proxy functionality
    proxies = utils.get_proxy_list(free_proxies=True)
    if proxies:
        print(f"Found {len(proxies)} working proxies")
        print(f"First few proxies: {proxies[:3]}")
    else:
        print("No proxies found")