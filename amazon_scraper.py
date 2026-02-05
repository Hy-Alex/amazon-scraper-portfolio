# amazon_scraper.py

import asyncio
import csv
import json
import logging
import random
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError

from config import (
    DEFAULT_COUNTRY,
    DEFAULT_MAX_PAGES,
    DEFAULT_HEADLESS,
    OUTPUT_DIR,
    REQUEST_TIMEOUT,
    PAGE_LOAD_TIMEOUT,
    USER_AGENTS,
    MIN_DELAY,
    MAX_DELAY
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AmazonScraper:
    """
    Amazon Product Scraper for search results pages.
    Designed for market research and educational purposes.
    """

    def __init__(
        self,
        keyword: str,
        max_pages: int = DEFAULT_MAX_PAGES,
        country: str = DEFAULT_COUNTRY,
        headless: bool = DEFAULT_HEADLESS
    ):
        self.keyword = keyword
        self.max_pages = max_pages
        self.country = country
        self.headless = headless
        self.base_url = f"https://www.{country}"
        self.products: List[Dict] = []

        # Ensure output directory exists
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    async def _init_browser(self):
        """Initialize browser and page with random user agent."""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=self.headless)

        user_agent = random.choice(USER_AGENTS)
        context = await browser.new_context(
            user_agent=user_agent,
            viewport={'width': 1920, 'height': 1080}
        )

        page = await context.new_page()
        page.set_default_timeout(REQUEST_TIMEOUT)

        logger.info(f"Browser initialized with User-Agent: {user_agent[:50]}...")
        return playwright, browser, context, page

    async def _navigate_to_search(self, page: Page, page_number: int = 1) -> bool:
        """Navigate to Amazon search results page."""
        try:
            search_url = f"{self.base_url}/s?k={self.keyword.replace(' ', '+')}"
            if page_number > 1:
                search_url += f"&page={page_number}"
            
            logger.info(f"Navigating to: {search_url}")
            await page.goto(search_url, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)
            
            # Wait for search results container
            await page.wait_for_selector('[data-component-type="s-search-result"]', timeout=REQUEST_TIMEOUT)
            
            # Random delay to mimic human behavior
            await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            
            return True
        except PlaywrightTimeoutError:
            logger.error(f"Timeout while loading search page {page_number}")
            return False
        except Exception as e:
            logger.error(f"Error navigating to search page: {str(e)}")
            return False

    async def _extract_product_data(self, page: Page) -> List[Dict]:
        """Extract product data from current search results page."""
        products = []
        
        try:
            # Get all product containers
            product_elements = await page.query_selector_all('[data-component-type="s-search-result"]')
            logger.info(f"Found {len(product_elements)} product elements")
            
            for element in product_elements:
                try:
                    product = await self._parse_product_element(element)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.warning(f"Error parsing product element: {str(e)}")
                    continue
            
            logger.info(f"Successfully extracted {len(products)} products")
            
        except Exception as e:
            logger.error(f"Error extracting product data: {str(e)}")
        
        return products

    async def _parse_product_element(self, element) -> Optional[Dict]:
        """Parse individual product element to extract data."""
        try:
            # ASIN
            asin = await element.get_attribute('data-asin')
            if not asin:
                return None

            # Title - multiple fallback selectors
            title = "N/A"
            title_selectors = [
                'h2 a span',
                'h2 span.a-text-normal',
                '[data-cy="title-recipe"] h2 span',
                'h2 a'
            ]
            for selector in title_selectors:
                title_elem = await element.query_selector(selector)
                if title_elem:
                    title = await title_elem.inner_text()
                    if title and title.strip():
                        break

            # Product URL - multiple fallback selectors
            product_url = ""
            url_selectors = [
                'h2 a',
                'a.a-link-normal[href*="/dp/"]',
                'a.s-no-outline[href*="/dp/"]',
                'a.a-link-normal.s-underline-text'
            ]
            for selector in url_selectors:
                url_elem = await element.query_selector(selector)
                if url_elem:
                    product_url = await url_elem.get_attribute('href') or ""
                    if product_url:
                        break
            if product_url and not product_url.startswith('http'):
                product_url = f"{self.base_url}{product_url}"

            # Price
            price = "N/A"
            currency = "USD"
            price_whole = await element.query_selector('.a-price-whole')
            price_fraction = await element.query_selector('.a-price-fraction')

            if price_whole:
                whole = await price_whole.inner_text()
                fraction = await price_fraction.inner_text() if price_fraction else "00"
                price = f"{whole.replace(',', '')}{fraction}".strip()

            # Currency symbol
            currency_elem = await element.query_selector('.a-price-symbol')
            if currency_elem:
                symbol = await currency_elem.inner_text()
                if symbol == '$':
                    currency = 'USD'
                elif symbol == '€':
                    currency = 'EUR'
                elif symbol == '£':
                    currency = 'GBP'

            # Rating - multiple fallback selectors
            rating = "N/A"
            rating_selectors = [
                '.a-icon-star-small .a-icon-alt',
                '.a-icon-star-mini .a-icon-alt',
                'i.a-icon-star .a-icon-alt',
                '[data-cy="reviews-ratings-slot"] .a-icon-alt',
                'span[data-action="a-popover"] .a-icon-alt'
            ]
            for selector in rating_selectors:
                rating_elem = await element.query_selector(selector)
                if rating_elem:
                    rating_text = await rating_elem.inner_text()
                    if rating_text:
                        # Extract rating from "X.X out of 5 stars" pattern
                        rating = rating_text.split(' ')[0]
                        if rating and rating != "N/A":
                            break

            # Review count - look for the actual review count element
            review_count = "0"
            # Try dedicated review count selectors first
            review_selectors = [
                'a[href*="#customerReviews"] span.a-size-base',
                'span.a-size-base.s-underline-text',
                '[data-cy="reviews-block"] span.a-size-base',
                'a[href*="customerReviews"] span'
            ]
            for selector in review_selectors:
                review_elem = await element.query_selector(selector)
                if review_elem:
                    review_text = await review_elem.inner_text()
                    if review_text:
                        # Extract numeric value (e.g., "1,234" -> "1234")
                        cleaned = review_text.replace(',', '').replace('.', '').strip()
                        if cleaned.isdigit():
                            review_count = cleaned
                            break

            # Fallback: try aria-label on review link
            if review_count == "0":
                review_link = await element.query_selector('a[href*="#customerReviews"]')
                if not review_link:
                    review_link = await element.query_selector('a[href*="customerReviews"]')
                if review_link:
                    aria_label = await review_link.get_attribute('aria-label')
                    if aria_label:
                        # Parse "X,XXX ratings" or similar patterns
                        match = re.search(r'([\d,]+)\s*(?:ratings?|reviews?)', aria_label, re.IGNORECASE)
                        if match:
                            review_count = match.group(1).replace(',', '')

            # Prime availability - multiple fallback selectors
            is_prime = False
            prime_selectors = [
                '[aria-label="Amazon Prime"]',
                'i.a-icon-prime',
                '[data-cy="prime-badge"]',
                '.s-prime',
                'i.a-icon.a-icon-prime'
            ]
            for selector in prime_selectors:
                prime_elem = await element.query_selector(selector)
                if prime_elem:
                    is_prime = True
                    break

            # Sponsored flag
            is_sponsored = False
            sponsored_elem = await element.query_selector('.s-sponsored-label-text')
            if sponsored_elem:
                is_sponsored = True

            return {
                'title': title.strip() if title else "N/A",
                'asin': asin,
                'price': price,
                'currency': currency,
                'rating': rating,
                'review_count': review_count,
                'is_prime': is_prime,
                'is_sponsored': is_sponsored,
                'product_url': product_url
            }

        except Exception as e:
            logger.warning(f"Error parsing product: {str(e)}")
            return None

    async def scrape(self) -> List[Dict]:
        """Main scraping method."""
        logger.info(f"Starting scrape for keyword: '{self.keyword}'")
        logger.info(f"Max pages: {self.max_pages}, Country: {self.country}")

        playwright = None
        browser = None
        context = None
        try:
            playwright, browser, context, page = await self._init_browser()

            for page_num in range(1, self.max_pages + 1):
                logger.info(f"Processing page {page_num}/{self.max_pages}")

                if await self._navigate_to_search(page, page_num):
                    products = await self._extract_product_data(page)
                    self.products.extend(products)
                else:
                    logger.warning(f"Failed to load page {page_num}, stopping scrape")
                    break

                # Delay between pages
                if page_num < self.max_pages:
                    await asyncio.sleep(random.uniform(MIN_DELAY * 2, MAX_DELAY * 2))

            logger.info(f"Scraping completed. Total products: {len(self.products)}")

        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
        finally:
            # Close in proper order: context -> browser -> playwright
            if context:
                await context.close()
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()

        return self.products

    def save_to_csv(self, filename: Optional[str] = None) -> str:
        """Save scraped data to CSV file."""
        if not self.products:
            logger.warning("No products to save")
            return ""
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"amazon_products_{timestamp}.csv"
        
        filepath = Path(OUTPUT_DIR) / filename
        
        try:
            fieldnames = [
                'title', 'asin', 'price', 'currency', 'rating',
                'review_count', 'is_prime', 'is_sponsored', 'product_url'
            ]
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.products)
            
            logger.info(f"Data saved to CSV: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error saving to CSV: {str(e)}")
            return ""

    def save_to_json(self, filename: Optional[str] = None) -> str:
        """Save scraped data to JSON file."""
        if not self.products:
            logger.warning("No products to save")
            return ""
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"amazon_products_{timestamp}.json"
        
        filepath = Path(OUTPUT_DIR) / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(self.products, jsonfile, indent=2, ensure_ascii=False)
            
            logger.info(f"Data saved to JSON: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error saving to JSON: {str(e)}")
            return ""


async def main():
    """Main execution function."""
    # Example usage
    scraper = AmazonScraper(
        keyword="laptop",
        max_pages=2,
        country="amazon.com"
    )
    
    # Perform scraping
    await scraper.scrape()
    
    # Save results
    scraper.save_to_csv("amazon_products.csv")
    scraper.save_to_json("amazon_products.json")


if __name__ == "__main__":
    asyncio.run(main())