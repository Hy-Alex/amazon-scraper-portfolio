# Amazon Product Scraper (Python + Playwright)

A production-ready Amazon search results scraper built with **Python** and **Playwright**.

This project is designed as a **freelancer portfolio example for Upwork**, focused on market research, price monitoring, and competitor analysis.

---

## Project Overview

This scraper extracts structured product data from **Amazon search result pages** based on a given keyword.

It is intentionally designed for **low-frequency, stable scraping**, prioritizing:

- Reliability over speed
- Clean and readable Python code
- Client-ready CSV / JSON output
- Real-world usability instead of aggressive crawling

---

## What This Scraper Does

- Scrapes Amazon search results by keyword
- Handles JavaScript-rendered pages using Playwright
- Supports pagination with configurable page limits
- Extracts key product information
- Exports results to **CSV** and **JSON**
- Suitable for real client delivery and freelance projects

---

## Example Target Page

https://www.amazon.com/s?k=laptop

---

## Extracted Data Fields

- title
- asin
- price
- currency
- rating
- review_count
- is_prime
- is_sponsored
- product_url

---

## Project Structure

amazon-scraper-portfolio/
├── amazon_scraper.py
├── config.py
├── requirements.txt
├── README.md
└── output/
    ├── amazon_products.csv
    └── amazon_products.json

---

## Installation

### Requirements

- Python 3.10+
- pip

### Setup

pip install -r requirements.txt
playwright install chromium

---

## How to Run

python amazon_scraper.py

Scraped data will be saved automatically to the output/ directory.

---

## Configuration

Edit config.py to adjust:

- Search keyword
- Maximum pages
- Request delays
- Headless mode

---

## Intended Use

- Market research
- Competitor analysis
- Price monitoring
- Freelance portfolio demonstration

---

## Legal & Ethical Notice

This project is provided for educational and portfolio demonstration purposes only.

Respect website terms of service and use reasonable request frequency.

---

## Author

Created as a professional freelance portfolio project for Upwork clients.
