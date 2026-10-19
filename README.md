# The Polite Scraper

A Python web scraper for collecting, cleaning, and validating book data from Books to Scrape.

## Target Classification

- **Target:** https://books.toscrape.com/
- **Purpose:** Books to Scrape is a practice sandbox designed for learning web scraping.
- **Scope:** The first three catalogue pages and their 60 book detail pages.
- **Data collected:** Book title, product URL, price, availability, rating, description, source page, and fetch timestamp.
- **robots.txt result:** Requested https://books.toscrape.com/robots.txt on 2026-10-18. The server returned HTTP 404 Not Found. Recorded as "no robots file found".
- **Responsible use:** A missing robots.txt file is not permission to scrape without limits. The scraper will identify itself, use timeouts, check HTTP status codes, wait between real requests, and cache downloaded pages.

I will not reuse this code on another site without checking its rules and terms first.
