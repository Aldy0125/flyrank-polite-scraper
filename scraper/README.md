# The Polite Scraper

A Python web scraper that collects, cleans, validates, and stores book data from Books to Scrape.

## 1. Project Overview

- **Assignment:** BE-05 - The Polite Scraper
- **Track:** Backend AI Engineering
- **Language:** Python 3.13
- **Target:** https://books.toscrape.com/
- **Scope:** The first three catalogue pages and their book detail pages.
- **Expected output:** 60 unique validated book records.

Books to Scrape is a practice website designed for learning web scraping.

## 2. Target Classification and Robots Check

- **Target classification:** Educational web scraping practice site.
- **robots.txt URL:** https://books.toscrape.com/robots.txt
- **Observed result:** HTTP 404 Not Found when checked on 2026-10-18.
- **Interpretation:** No robots.txt file was found at the checked URL. This does not mean unrestricted scraping is permitted.

## 3. Features

- Discovers book URLs from the first three catalogue pages.
- Collects eight raw fields for each book.
- Converts price text into a numeric GBP value.
- Validates records using Pydantic.
- Stores valid records in `output/books.json`.
- Stores invalid records and their reasons in `output/errors.json`.
- Generates `output/run-report.json`.
- Uses a local HTML cache to avoid unnecessary repeated requests.
- Handles failed pages without stopping the entire run.

## 4. Installation

Python 3.10 or later is required.

Install dependencies from the repository root:

```powershell
python -m pip install requests beautifulsoup4 pydantic
```

## 5. Run the Scraper

From the repository root, run:

```powershell
python scraper/src/main.py
```

The program reads cached HTML when available. Missing pages are requested with a timeout and a delay between network requests.

## 6. Record Schema

Each valid record contains the following fields:

| Field | Type | Description |
|---|---|---|
| `title` | string | Book title |
| `product_url` | string | Canonical HTTPS product URL |
| `price_text` | string | Original price text, such as `£51.77` |
| `price_gbp` | number | Normalized price, such as `51.77` |
| `availability_text` | string | Availability information |
| `rating_text` | string | Rating label |
| `description` | string or null | Book description |
| `source_page` | string | Catalogue page where the book was discovered |
| `fetched_at` | datetime string | Timestamp associated with record extraction |

## 7. Responsible Scraping Practices

- Identify the scraper with a descriptive User-Agent.
- Use a request timeout.
- Wait at least 500 milliseconds before each real network request.
- Cache downloaded HTML and reuse it during development.
- Check HTTP status codes.
- Do not retry HTTP 403 or 404 responses.
- Limit collection to the required three catalogue pages.
- Use an official API when one is available.
- Never bypass logins, paywalls, or access restrictions.
- Collect only the data required for the assignment.

## 8. Validation and Output

The scraper validates each normalized record using Pydantic.

- `output/books.json` contains valid records.
- `output/errors.json` contains records that fail processing or validation.
- `output/run-report.json` contains execution metrics and failure details.

## 9. Verified Run Report

The following values came from one observed run using the existing local cache:

```json
{
  "catalogue_pages_processed": 3,
  "discovered_books": 60,
  "detail_pages_processed": 60,
  "pages_fetched": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0,
  "failed_page_urls": [],
  "duration_seconds": 0.444
}
```

The duration above reflects a cache-backed run. It does not represent the time required to download all pages from the network.

## 10. Why No Browser Is Needed

The required book data is available in the HTML returned by the server. Requests and Beautiful Soup can process that HTML directly, so a browser would add unnecessary complexity and resource cost for this assignment.

## 11. Limitations

- The scraper is scoped to the first three catalogue pages.
- HTML selectors depend on the current structure of the target website.
- Cached content may become outdated.
- The reported execution time depends on whether pages are cached.

## 12. AI Ethics Note

This project is intended for educational practice. Scraping should remain limited, transparent, and respectful of website rules and server resources.