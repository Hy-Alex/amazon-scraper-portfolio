# Amazon Scraper (Python + Playwright)

## Short Summary

A Python-based Amazon product scraper that extracts structured product data and prepares a clean client-ready dataset for product research and market analysis.

## What This Scraper Does

This project uses a Python + Playwright stack to collect product listings from Amazon search result pages. It captures key commercial fields (title, price, rating, reviews, product URL, and ad flag), then supports post-processing into delivery-ready files for client reporting.

## Key Features

- Browser automation with Playwright for JavaScript-rendered pages
- Structured extraction from Amazon search result listings
- Pagination support for multi-page collection
- CSV and JSON export support
- Separate dataset cleanup flow in `prepare_client_dataset.py`
- Output can be transformed into a client-ready CSV for delivery

## Output Fields

The scraper outputs these fields:

- `title`
- `asin`
- `price`
- `currency`
- `rating`
- `review_count`
- `is_prime`
- `is_sponsored`
- `product_url`

## Example Use Cases

- Product research for a niche or keyword segment
- Competitor listing snapshots for pricing comparison
- Sponsored vs non-sponsored result review
- Weekly dataset refresh for marketplace monitoring

## Project Structure

```text
amazon-scraper-portfolio/
├── amazon_scraper.py
├── prepare_client_dataset.py
├── config.py
├── requirements.txt
├── README.md
└── output/
```

## Setup

1. Clone the repository:

```bash
git clone https://github.com/Hy-Alex/amazon-scraper-portfolio.git
cd amazon-scraper-portfolio
```

2. Create and activate a virtual environment.

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Install Playwright browser binaries:

```bash
playwright install chromium
```

## How to Run

Run the scraper:

```bash
python amazon_scraper.py
```

Prepare a cleaned client dataset:

```bash
python prepare_client_dataset.py
```

## Notes / Limitations

- Amazon page structure can change over time, which may require selector updates.
- Amazon may present anti-bot checks, CAPTCHAs, or region-based access differences depending on network conditions.
- Results and availability can vary by locale, account state, and request timing.