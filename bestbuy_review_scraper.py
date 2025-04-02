import time
import uuid
import pandas as pd
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tqdm import tqdm
from loguru import logger
import platform
import os

class BestBuyReviewScraper:
    def __init__(self, headless=False, timeout=10, wait_time=(3, 7)):
        """
        Initialize the BestBuy Review Scraper
        
        Args:
            headless (bool): Run browser in headless mode
            timeout (int): Maximum wait time for elements in seconds
            wait_time (tuple): Range of seconds to wait between actions (min, max)
        """
        logger.info("Initializing BestBuy Review Scraper")
        self.timeout = timeout
        self.wait_time = wait_time
        
        # Set up Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        
        # Set random user agent
        ua = UserAgent()
        user_agent = ua.random
        chrome_options.add_argument(f'user-agent={user_agent}')
        
        # Add other options to avoid detection
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Initialize WebDriver using Selenium's built-in manager
        from selenium.webdriver.chrome.service import Service
        
        # Use Selenium's built-in webdriver manager
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Store reviews
        self.reviews = []
        
    def __del__(self):
        """Close the browser when the object is destroyed"""
        if hasattr(self, 'driver'):
            self.driver.quit()
    
    def random_sleep(self):
        """Sleep for a random amount of time to avoid detection"""
        time.sleep(random.uniform(self.wait_time[0], self.wait_time[1]))
    
    def navigate_to_product(self, product_url):
        """Navigate to the product page and go to reviews section"""
        logger.info(f"Navigating to product: {product_url}")
        self.driver.get(product_url)
        self.random_sleep()
        
        # Wait for page to load
        try:
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            logger.info("Page loaded successfully")
        except (TimeoutException, NoSuchElementException) as e:
            logger.error(f"Failed to load page: {e}")
            return False
        
        # Scroll down to make reviews visible - based on your screenshot
        self.driver.execute_script("window.scrollBy(0, 700);")
        self.random_sleep()
        
        # Look for "Customer Reviews" section as shown in your screenshot
        try:
            # Try to find the Customer Reviews section
            reviews_section = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'customer-reviews') or contains(text(), 'Customer Reviews')]"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", reviews_section)
            logger.info("Found and scrolled to Customer Reviews section")
            self.random_sleep()
            
            # Take a screenshot for debugging
            self.driver.save_screenshot("reviews_section.png")
            logger.info("Saved screenshot of reviews section to reviews_section.png")
            return True
        except (TimeoutException, NoSuchElementException) as e:
            logger.error(f"Failed to find Customer Reviews section: {e}")
            
            # Try another approach with the ratings section
            try:
                # Look for the ratings or any section with reviews
                ratings_element = WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.XPATH, "//section[contains(@class, 'rating') or contains(@class, 'review') or contains(@id, 'review')]"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", ratings_element)
                logger.info("Found and scrolled to ratings/reviews section using alternative method")
                
                # Take a screenshot for debugging
                self.driver.save_screenshot("reviews_section_alt.png")
                logger.info("Saved screenshot of alternative reviews section to reviews_section_alt.png")
                
                self.random_sleep()
                return True
            except (TimeoutException, NoSuchElementException) as e2:
                logger.error(f"Failed to find any reviews section: {e2}")
                
                # Last resort: just scroll down to where reviews usually are
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
                logger.info("Scrolled down to where reviews typically are")
                self.random_sleep()
                
                # Take a screenshot for debugging
                self.driver.save_screenshot("page_scroll.png")
                logger.info("Saved screenshot of scrolled page to page_scroll.png")
                return True
    
    def select_filter(self, filter_option="most-helpful"):
        """
        Select a filter for the reviews
        
        Args:
            filter_option (str): One of 'most-helpful', 'newest', 'highest-rating', 
                                 'lowest-rating', 'most-relevant'
        """
        logger.info(f"Selecting filter: {filter_option}")
        
        # Map filter options to their likely text in the UI
        filter_mapping = {
            "most-helpful": "Most Helpful",
            "newest": "Newest",
            "highest-rating": "Highest Rating",
            "lowest-rating": "Lowest Rating",
            "most-relevant": "Most Relevant"
        }
        
        try:
            # Based on your screenshot, look for the dropdown or filter options
            filter_selectors = [
                # Look for "Most Relevant" dropdown in the screenshot
                "//button[contains(@class, 'dropdown') or contains(@class, 'filter')]",
                "//div[contains(@class, 'dropdown') or contains(@class, 'filter')]",
                "//button[contains(text(), 'Sort')]",
                "//div[contains(text(), 'Sort')]",
                "//select[contains(@class, 'sort') or contains(@class, 'filter')]"
            ]
            
            found_filter = False
            for selector in filter_selectors:
                try:
                    filter_elements = self.driver.find_elements(By.XPATH, selector)
                    if filter_elements:
                        for element in filter_elements:
                            try:
                                element.click()
                                logger.info(f"Clicked on potential filter element: {element.text if element.text else 'no text'}")
                                self.random_sleep()
                                found_filter = True
                                break
                            except:
                                continue
                    if found_filter:
                        break
                except:
                    continue
            
            if not found_filter:
                logger.warning("Could not find any filter dropdown. Proceeding with default sorting.")
                return False
            
            # Now try to select the specific filter option
            filter_text = filter_mapping.get(filter_option, "Most Relevant")
            filter_option_selectors = [
                f"//div[contains(text(), '{filter_text}')]",
                f"//span[contains(text(), '{filter_text}')]",
                f"//option[contains(text(), '{filter_text}')]",
                f"//li[contains(text(), '{filter_text}')]"
            ]
            
            found_option = False
            for selector in filter_option_selectors:
                try:
                    option_elements = self.driver.find_elements(By.XPATH, selector)
                    if option_elements:
                        for element in option_elements:
                            try:
                                element.click()
                                logger.info(f"Selected filter: {filter_text}")
                                self.random_sleep()
                                found_option = True
                                return True
                            except:
                                continue
                    if found_option:
                        break
                except:
                    continue
            
            if not found_option:
                logger.warning(f"Could not select filter option: {filter_text}. Proceeding with default sorting.")
            
            return found_option
        except Exception as e:
            logger.error(f"Error during filter selection: {e}")
            return False
    
    def load_all_reviews(self, max_reviews=None):
        """
        Click 'Show More' button until all reviews are loaded or max_reviews is reached
        
        Args:
            max_reviews (int, optional): Maximum number of reviews to load
        """
        reviews_loaded = 0
        
        # Take a screenshot before trying to load reviews
        self.driver.save_screenshot("before_loading_reviews.png")
        logger.info("Saved screenshot before loading reviews")
        
        # Try different selectors for review elements based on the screenshot
        review_selectors = [
            ".review-item", 
            ".review-list-item",
            "[class*='review']",
            ".customer-review",
            ".ratings-reviews"
        ]
        
        # Find which selector works for reviews
        working_selector = None
        for selector in review_selectors:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                working_selector = selector
                logger.info(f"Found reviews using selector: {selector} (count: {len(elements)})")
                break
        
        if not working_selector:
            logger.warning("Could not find any reviews using standard selectors")
        
        # Try to identify "Show More" or pagination buttons
        show_more_selectors = [
            "button.show-more-button",
            "button[class*='more']",
            "button[class*='load']",
            "a[class*='more']",
            "span[class*='more']",
            ".pagination button",
            "button.pagination",
            "a.pagination",
            "button[class*='next']",
            "a[class*='next']"
        ]
        
        # Try clicking any "Show More" button
        max_attempts = 5  # Limit attempts to prevent infinite loops
        attempts = 0
        
        while attempts < max_attempts:
            attempts += 1
            try:
                # Count current reviews
                current_reviews = 0
                if working_selector:
                    current_reviews = len(self.driver.find_elements(By.CSS_SELECTOR, working_selector))
                
                # Take a screenshot to see what's visible
                self.driver.save_screenshot(f"reviews_attempt_{attempts}.png")
                logger.info(f"Saved screenshot of reviews attempt {attempts}")
                
                # Check if we've reached max_reviews
                if max_reviews and current_reviews >= max_reviews:
                    logger.info(f"Reached maximum number of reviews: {max_reviews}")
                    break
                
                # Try each "Show More" selector
                clicked = False
                for selector in show_more_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                    self.random_sleep(1, 2)
                                    element.click()
                                    logger.info(f"Clicked on potential 'Show More' button using selector: {selector}")
                                    self.random_sleep(2, 4)
                                    clicked = True
                                    break
                        if clicked:
                            break
                    except:
                        continue
                
                if not clicked:
                    logger.info("No more 'Show More' buttons found")
                    break
                
                # Check if we got more reviews
                if working_selector:
                    new_reviews = len(self.driver.find_elements(By.CSS_SELECTOR, working_selector))
                    if new_reviews <= current_reviews:
                        logger.info("No new reviews were loaded")
                        break
                    
                    reviews_loaded = new_reviews
                    logger.info(f"Loaded {reviews_loaded} reviews so far")
                
            except Exception as e:
                logger.error(f"Error loading more reviews: {e}")
                break
        
        # Final screenshot after loading reviews
        self.driver.save_screenshot("after_loading_reviews.png")
        logger.info("Saved screenshot after attempting to load all reviews")
    
    def parse_reviews(self):
        """Parse all loaded reviews on the page"""
        logger.info("Parsing reviews")
        
        # Take a screenshot before parsing
        self.driver.save_screenshot("before_parsing.png")
        logger.info("Saved screenshot before parsing reviews")
        
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Try multiple selectors to find reviews based on your screenshot
        review_selectors = [
            "div.review-item",
            "div.review-list-item", 
            "div[class*='review']",
            "div.customer-review",
            "article.review",
            "div.ratings-reviews div"
        ]
        
        all_reviews = []
        for selector in review_selectors:
            reviews = soup.select(selector)
            if reviews:
                logger.info(f"Found {len(reviews)} reviews using selector: {selector}")
                all_reviews = reviews
                break
        
        if not all_reviews:
            # Try a more generic approach - look for elements with ratings
            potential_reviews = soup.find_all(["div", "article", "section"], 
                                              class_=lambda c: c and any(x in c for x in ["review", "rating", "comment"]))
            if potential_reviews:
                logger.info(f"Found {len(potential_reviews)} potential reviews using class-based search")
                all_reviews = potential_reviews
        
        logger.info(f"Found {len(all_reviews)} reviews to parse")
        
        for review in tqdm(all_reviews, desc="Parsing reviews"):
            try:
                # Extract review details
                review_id = str(uuid.uuid4())  # Generate unique ID for the review
                
                # Title - look for any headings
                title_elem = None
                for tag in ["h3", "h4", "h5", "strong", "span", "div"]:
                    title_candidates = review.find_all(tag)
                    if title_candidates:
                        title_elem = title_candidates[0]
                        break
                
                title = title_elem.get_text(strip=True) if title_elem else "No Title"
                
                # Get review text - look for paragraph elements or div content
                text_candidates = review.find_all(["p", "div", "span"])
                review_text = ""
                for elem in text_candidates:
                    if elem.name == "p" or "content" in (elem.get("class", []) or []):
                        text = elem.get_text(strip=True)
                        if len(text) > len(review_text):
                            review_text = text
                
                if not review_text:
                    # Get all text from the review if we couldn't identify specific content
                    review_text = review.get_text(strip=True)
                    if title in review_text:
                        review_text = review_text.replace(title, "", 1).strip()
                
                # Date - look for various date formats
                date_elem = None
                date_candidates = review.find_all(["time", "span", "div"], 
                                                class_=lambda c: c and any(x in c for x in ["date", "time", "when"]))
                if date_candidates:
                    date_elem = date_candidates[0]
                
                date_str = date_elem.get_text(strip=True) if date_elem else ""
                date = "Unknown"
                
                if date_str:
                    try:
                        # Try different date formats
                        if "," in date_str:  # Format like "March 31, 2025"
                            date_obj = datetime.strptime(date_str, "%B %d, %Y")
                            date = date_obj.strftime("%Y-%m-%d")
                        elif "-" in date_str:  # Format like "2025-04-01"
                            date = date_str
                        else:
                            # Just keep the original string
                            date = date_str
                    except:
                        date = date_str
                
                # Rating - look for star ratings
                rating = 0
                # Check for filled stars
                star_elements = review.find_all(["span", "i", "div"], 
                                              class_=lambda c: c and any(x in c for x in ["star", "rating", "filled"]))
                if star_elements:
                    # Count filled stars
                    rating = len(star_elements)
                
                # If no rating found, check for numeric ratings
                if rating == 0:
                    rating_text_elements = review.find_all(text=lambda t: t and any(x in t for x in ["/5", "out of 5", "stars"]))
                    if rating_text_elements:
                        for elem in rating_text_elements:
                            try:
                                # Extract number from text like "4.2/5" or "4.2 out of 5"
                                import re
                                numbers = re.findall(r'\d+\.\d+|\d+', elem)
                                if numbers:
                                    rating = float(numbers[0])
                                    break
                            except:
                                continue
                
                # Reviewer name
                name_elem = None
                name_candidates = review.find_all(["span", "div", "a"], 
                                               class_=lambda c: c and any(x in c for x in ["author", "reviewer", "name", "user"]))
                if name_candidates:
                    name_elem = name_candidates[0]
                
                reviewer_name = name_elem.get_text(strip=True) if name_elem else "Anonymous"
                
                # Add to reviews list if we have at least some meaningful content
                if review_text or title != "No Title":
                    self.reviews.append({
                        "review_id": review_id,
                        "title": title,
                        "review_text": review_text,
                        "date": date,
                        "rating": rating,
                        "source": "BestBuy Canada",
                        "reviewer_name": reviewer_name
                    })
                
            except Exception as e:
                logger.error(f"Error parsing review: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(self.reviews)} reviews")
    
    def save_to_csv(self, filename="bestbuy_reviews.csv"):
        """Save the reviews to a CSV file"""
        if not self.reviews:
            logger.warning("No reviews to save")
            return
        
        df = pd.DataFrame(self.reviews)
        df.to_csv(filename, index=False)
        logger.success(f"Saved {len(self.reviews)} reviews to {filename}")
        return df
    
    def scrape_product_reviews(self, product_url, filter_option="most-helpful", max_reviews=None):
        """
        Main method to scrape reviews for a product
        
        Args:
            product_url (str): URL of the product page
            filter_option (str): Filter to apply to reviews
            max_reviews (int, optional): Maximum number of reviews to scrape
        
        Returns:
            pandas.DataFrame: DataFrame containing the scraped reviews
        """
        try:
            # Navigate to the product and reviews section
            if not self.navigate_to_product(product_url):
                return None
            
            # Select the filter
            self.select_filter(filter_option)
            
            # Load all reviews
            self.load_all_reviews(max_reviews)
            
            # Parse the reviews
            self.parse_reviews()
            
            # Save and return the reviews
            return self.save_to_csv()
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            return None

# Example usage
if __name__ == "__main__":
    # Example product URL
    product_url = "https://www.bestbuy.ca/en-ca/product/samsung-65-4k-uhd-hdr-qled-tizen-smart-tv-qn65q80cafxzc-titan-black/17167585"
    
    scraper = BestBuyReviewScraper(headless=False)
    reviews_df = scraper.scrape_product_reviews(
        product_url=product_url,
        filter_option="most-helpful",
        max_reviews=100
    )
    
    print(f"Scraped {len(scraper.reviews)} reviews")
