# Amazon Search Scraper (Python + Playwright)

A **production-ready Amazon search results scraper** built with **Python** and **Playwright**, specifically optimized for **freelance client delivery** and long-term maintenance.

This project demonstrates a focus on **reliable, maintainable, and environment-compatible web automation solutions** for real-world business intelligence.

---

## 🎯 Why This Project Exists (Client Perspective)

Most clients requiring Amazon data face several automation hurdles. This scraper is engineered to solve:
* **JavaScript-Heavy Pages:** Uses Playwright to handle dynamic content that traditional scrapers miss.
* **Regional Environment Differences:** Designed to run consistently across different locales and networks.
* **Anti-Bot Friction:** Balances extraction depth with site-respecting delays to minimize blocks.
* **Data Integrity:** Prioritizes **stability over brute-force speed** and **data correctness over speculative extraction.**

---

## ✨ Key Capabilities

* **Dynamic Rendering:** Full support for JavaScript-rendered search results.
* **Smart Ad Filtering:** Automatically identifies and labels **Sponsored/Ad** results to ensure organic data purity.
* **Pagination Management:** Seamlessly crawls through multiple result pages.
* **Dual-Format Export:** Generates clean, structured data in both **CSV** and **JSON**.
* **Human-Centric Interaction:** Mimics real user behavior through viewport management and randomized timing.

---

## 📊 Extracted Data Fields

| Field | Description |
| :--- | :--- |
| `title` | Full product name as displayed on the search page |
| `asin` | Amazon Standard Identification Number |
| `price` | Current listed price (including currency symbol) |
| `rating` | Star rating (e.g., 4.5) |
| `review_count` | Total number of verified customer reviews |
| `is_sponsored` | **Indicates whether the result is a paid advertisement** |
| `is_prime` | Prime eligibility status |
| `product_url` | Direct, cleaned link to the product detail page |

---

## ⚙️ Environment & Stability Strategy

To ensure **maximum installation stability** across diverse client environments (local machines, VPS, or Docker), this project is locked to:
`playwright==1.40.0`

**Engineering Rationale:**
Newer versions of automation libraries can introduce breaking changes in browser binaries. By pinning **v1.40.0**, I ensure:
1.  **Predictable Installation:** Zero-fail browser downloads in restricted environments.
2.  **Stable Execution:** Proven compatibility with stable Chromium builds.
3.  **Low Maintenance:** Easier client-side deployment without constant troubleshooting.

---

## 🚀 Installation & Usage

### 1. Requirements
* Python 3.10+
* pip

### 2. Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install the verified Chromium binary
playwright install chromium