# config.py

"""
Configuration file for Amazon Scraper.
Modify these settings based on your requirements.
"""

# Amazon domain settings
DEFAULT_COUNTRY = "amazon.com"  # Options: amazon.com, amazon.co.uk, amazon.de, etc.

# Scraping parameters
DEFAULT_MAX_PAGES = 2  # Maximum number of search result pages to scrape
DEFAULT_HEADLESS = False  # Run browser in headless mode (False = visible)

# Output settings
OUTPUT_DIR = "output"  # Directory to save output files

# Timeout settings (milliseconds)
REQUEST_TIMEOUT = 30000  # 30 seconds
PAGE_LOAD_TIMEOUT = 60000  # 60 seconds

# Request delays (seconds) - to avoid overwhelming the server
MIN_DELAY = 1.5
MAX_DELAY = 3.0

# User agent rotation for diversity
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]