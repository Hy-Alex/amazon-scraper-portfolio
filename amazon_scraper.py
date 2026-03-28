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
from urllib.parse import urlparse

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

# Debug toggles for timeout diagnosis (keep temporary during investigation)
DEBUG_DIAGNOSTICS = True
DEBUG_OUTPUT_DIR = Path(OUTPUT_DIR) / 'debug'


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

        logger.info(
            'Scraper domain config -> country=%s, default_country=%s, base_url=%s',
            self.country,
            DEFAULT_COUNTRY,
            self.base_url
        )

    async def _init_browser(self):
        """Initialize browser and page with random user agent."""
        playwright = await async_playwright().start()
        effective_headless = False if DEBUG_DIAGNOSTICS else self.headless
        browser = await playwright.chromium.launch(headless=effective_headless)

        user_agent = random.choice(USER_AGENTS)
        context = await browser.new_context(
            user_agent=user_agent,
            viewport={'width': 1920, 'height': 1080}
        )

        page = await context.new_page()
        page.set_default_timeout(REQUEST_TIMEOUT)

        logger.info(
            f"Browser initialized with User-Agent: {user_agent[:50]}... "
            f"(headless={effective_headless})"
        )
        return playwright, browser, context, page

    async def _save_debug_artifacts(
        self,
        page: Page,
        page_number: int,
        stage: str,
        error_message: str = ""
    ) -> None:
        """Save URL/title/screenshot/HTML and anti-bot indicators for failed loads."""
        DEBUG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = f"page_{page_number}_{stage}_{timestamp}"
        screenshot_path = DEBUG_OUTPUT_DIR / f"{base_name}.png"
        html_path = DEBUG_OUTPUT_DIR / f"{base_name}.html"
        info_path = DEBUG_OUTPUT_DIR / f"{base_name}.txt"

        final_url = page.url
        try:
            title = await page.title()
        except Exception:
            title = "N/A"

        try:
            html = await page.content()
        except Exception:
            html = ""

        anti_bot_phrases = [
            "captcha",
            "robot check",
            "enter the characters",
            "sorry, we just need to make sure you're not a robot"
        ]
        combined_text = f"{title}\n{html}".lower()
        detected_phrases = [phrase for phrase in anti_bot_phrases if phrase in combined_text]

        try:
            await page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception as e:
            logger.warning(f"Could not save screenshot for page {page_number}: {str(e)}")

        try:
            html_path.write_text(html, encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not save HTML for page {page_number}: {str(e)}")

        debug_lines = [
            f"stage: {stage}",
            f"error: {error_message or 'N/A'}",
            f"final_url: {final_url}",
            f"page_title: {title}",
            f"anti_bot_detected: {'yes' if detected_phrases else 'no'}",
            f"anti_bot_matches: {', '.join(detected_phrases) if detected_phrases else 'none'}",
            f"screenshot: {screenshot_path}",
            f"html: {html_path}"
        ]
        info_path.write_text("\n".join(debug_lines), encoding="utf-8")

        logger.error(f"Debug artifacts saved: {info_path}")
        logger.error(f"Final URL: {final_url}")
        logger.error(f"Page title: {title}")
        if detected_phrases:
            logger.error(f"Possible anti-bot page detected: {detected_phrases}")

    async def _navigate_to_search(self, page: Page, page_number: int = 1) -> bool:
        """Navigate to Amazon search results page."""
        search_url = f"{self.base_url}/s?k={self.keyword.replace(' ', '+')}"
        if page_number > 1:
            search_url += f"&page={page_number}"

        logger.info(f"Constructed search URL (before goto): {search_url}")

        try:
            response = await page.goto(search_url, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout during page.goto on page {page_number}: {str(e)}")
            await self._save_debug_artifacts(page, page_number, "goto_timeout", str(e))
            return False
        except Exception as e:
            logger.error(f"Error during page.goto on page {page_number}: {str(e)}")
            await self._save_debug_artifacts(page, page_number, "goto_error", str(e))
            return False

        final_url = page.url
        final_title = await page.title()
        logger.info(f"Final URL after goto: {final_url}")
        logger.info(f"Page title after goto: {final_title}")

        if response:
            final_request = response.request
            redirect_chain = [final_request.url]
            previous_request = final_request.redirected_from
            while previous_request:
                redirect_chain.append(previous_request.url)
                previous_request = previous_request.redirected_from
            redirect_chain.reverse()

            logger.info(
                f"Navigation response -> status={response.status}, response_url={response.url}"
            )
            if len(redirect_chain) > 1:
                logger.info(f"Redirect chain: {' -> '.join(redirect_chain)}")

        expected_host = urlparse(search_url).netloc
        final_host = urlparse(final_url).netloc
        if expected_host and final_host and expected_host != final_host:
            logger.warning(
                f"Marketplace/domain redirect detected: expected_host={expected_host}, final_host={final_host}"
            )

        result_selectors = [
            '[data-component-type="s-search-result"]',
            'div.s-main-slot div[data-asin]',
            '[data-asin]:has(h2)'
        ]
        per_selector_timeout = max(5000, REQUEST_TIMEOUT // len(result_selectors))

        for selector in result_selectors:
            try:
                await page.wait_for_selector(
                    selector,
                    state="attached",
                    timeout=per_selector_timeout
                )
                logger.info(f"Search results detected with selector: {selector}")

                # Random delay to mimic human behavior
                await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
                return True
            except PlaywrightTimeoutError:
                logger.warning(f"Selector timeout on page {page_number}: {selector}")

        logger.error(f"Timeout waiting for search results on page {page_number}")
        await self._save_debug_artifacts(
            page,
            page_number,
            "results_selector_timeout",
            "All search result selectors timed out"
        )
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






