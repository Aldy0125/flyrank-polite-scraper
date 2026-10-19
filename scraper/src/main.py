
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
import json
import re
import time

import requests
from bs4 import BeautifulSoup
from pydantic import ValidationError

from models import BookRecord


BASE_DIR = Path(__file__).resolve().parents[1]
CACHE_DIR = BASE_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "output"

CATALOGUE_URL = "https://books.toscrape.com/"
TIMEOUT = 10
REQUEST_DELAY = 0.5

HEADERS = {
    "User-Agent": (
        "AldyFlyRankBE05/1.0 "
        "(FlyRank internship learning project)"
    )
}

RUN_METRICS = {
    "pages_fetched": 0,
    "cache_hits": 0,
    "catalogue_pages_processed": 0,
    "failed_page_urls": set(),
}


def get_page(url, cache_file):
    """Read cached HTML or fetch it politely."""

    if cache_file.exists():
        content = cache_file.read_bytes()
        RUN_METRICS["cache_hits"] += 1
        print(f"CACHE HIT bytes={len(content)}")
        return BeautifulSoup(content, "html.parser")

    # Retry paling banyak sekali untuk timeout atau HTTP 5xx.
    for attempt in range(2):
        # Jeda sebelum setiap permintaan jaringan.
        time.sleep(REQUEST_DELAY)

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=TIMEOUT,
            )

        except requests.RequestException as error:
            if attempt == 0:
                print(f"RETRY after request error: {url}")
                continue

            RUN_METRICS["failed_page_urls"].add(url)
            print(f"FETCH ERROR url={url}: {error}")
            return None

        status_code = response.status_code

        if status_code == 200:
            content = response.content

            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file.write_bytes(content)

            RUN_METRICS["pages_fetched"] += 1

            print(
                f"FETCH status=200 bytes={len(content)}"
            )

            return BeautifulSoup(content, "html.parser")

        # Jangan mengulangi permintaan untuk 403 atau 404.
        if 500 <= status_code < 600 and attempt == 0:
            print(
                f"RETRY status={status_code} url={url}"
            )
            continue

        RUN_METRICS["failed_page_urls"].add(url)

        print(
            f"FETCH FAILED status={status_code} url={url}"
        )
        return None

    RUN_METRICS["failed_page_urls"].add(url)
    return None


def discover_books():
    """Discover unique books from the first three catalogue pages."""

    current_url = CATALOGUE_URL
    books = {}

    for page_number in range(1, 4):
        cache_file = (
            CACHE_DIR / f"catalogue-page-{page_number}.html"
        )

        soup = get_page(current_url, cache_file)

        if soup is None:
            print(
                f"Catalogue page {page_number} failed."
            )
            break

        RUN_METRICS["catalogue_pages_processed"] += 1

        for link in soup.select("article.product_pod h3 a"):
            href = link.get("href")

            if not href:
                continue

            book_url = urljoin(current_url, href)
            title = (
                link.get("title")
                or link.get_text(strip=True)
            )

            books[book_url] = {
                "title": title,
                "url": book_url,
                "source_page": current_url,
            }

        next_link = soup.select_one("li.next a")

        if page_number < 3:
            if next_link is None:
                print("Next catalogue link not found.")
                break

            current_url = urljoin(
                current_url,
                next_link["href"],
            )

    print(
        "catalogue_pages="
        f"{RUN_METRICS['catalogue_pages_processed']}"
    )
    print(f"discovered={len(books)}")
    print(f"unique_urls={len(books)}")

    return books


def clean_description(description_node):
    """Normalize description whitespace and remove a repeated opening."""

    if description_node is None:
        return None

    description = description_node.get_text(
        " ",
        strip=True,
    )

    description = re.sub(
        r"\s+",
        " ",
        description,
    ).strip()

    if not description:
        return None

    # Beberapa halaman dapat mengulang kalimat pembuka.
    first_sentence = re.match(
        r"(.+?[.!?])(?:\s|$)",
        description,
    )

    if first_sentence:
        opening = first_sentence.group(1)

        second_occurrence = description.find(
            opening,
            len(opening),
        )

        if second_occurrence != -1:
            description = description[
                second_occurrence:
            ].strip()

    return description or None


def extract_book_details(book):
    """Extract the eight raw fields from a book detail page."""

    product_url = book["url"]
    product_path = urlparse(product_url).path
    book_id = Path(product_path).parent.name

    cache_file = CACHE_DIR / f"book-{book_id}.html"
    soup = get_page(product_url, cache_file)

    if soup is None:
        return None

    title_node = soup.select_one(".product_main h1")
    price_node = soup.select_one(
        ".product_main .price_color"
    )
    availability_node = soup.select_one(
        ".product_main .availability"
    )
    rating_node = soup.select_one(
        ".product_main .star-rating"
    )

    description_heading = soup.select_one(
        "#product_description"
    )

    description_node = (
        description_heading.find_next_sibling("p")
        if description_heading
        else None
    )

    rating_text = None

    if rating_node:
        rating_text = next(
            (
                item
                for item in rating_node.get("class", [])
                if item != "star-rating"
            ),
            None,
        )

    return {
        "title": (
            title_node.get_text(strip=True)
            if title_node
            else book["title"]
        ),
        "product_url": product_url,
        "price_text": (
            price_node.get_text(strip=True)
            if price_node
            else None
        ),
        "availability_text": (
            availability_node.get_text(" ", strip=True)
            if availability_node
            else None
        ),
        "rating_text": rating_text,
        "description": clean_description(
            description_node
        ),
        "source_page": book["source_page"],
        "fetched_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }


def normalize_price(price_text):
    """Convert a price such as £51.77 into a numeric value."""

    if not isinstance(price_text, str):
        raise ValueError("Price text is missing.")

    cleaned = (
        price_text
        .replace("£", "")
        .replace(",", "")
        .strip()
    )

    if not re.fullmatch(
        r"\d+(?:\.\d{1,2})?",
        cleaned,
    ):
        raise ValueError(
            f"Invalid price format: {price_text!r}"
        )

    return float(cleaned)


def save_json(path, data):
    """Save readable UTF-8 JSON."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main():
    started_at = datetime.now(timezone.utc)
    start_clock = time.perf_counter()

    books = discover_books()

    valid_records = []
    invalid_records = []
    detail_pages = 0

    for index, book in enumerate(
        books.values(),
        start=1,
    ):
        raw_record = None

        try:
            raw_record = extract_book_details(book)

            if raw_record is None:
                invalid_records.append({
                    "product_url": book["url"],
                    "reason": (
                        "Could not fetch or parse book page."
                    ),
                })
                continue

            detail_pages += 1

            price_gbp = normalize_price(
                raw_record["price_text"]
            )

            cleaned_record = {
                **raw_record,
                "price_gbp": price_gbp,
            }

            validated_record = BookRecord.model_validate(
                cleaned_record
            )

            valid_records.append(
                validated_record.model_dump(
                    mode="json"
                )
            )

        except (ValueError, ValidationError) as error:
            invalid_records.append({
                "product_url": book["url"],
                "reason": str(error),
                "raw_record": raw_record,
            })

        except Exception as error:
            invalid_records.append({
                "product_url": book["url"],
                "reason": f"Unexpected error: {error}",
                "raw_record": raw_record,
            })

        finally:
            if index % 10 == 0:
                print(
                    f"detail_progress={index}/{len(books)} "
                    f"valid={len(valid_records)} "
                    f"invalid={len(invalid_records)}"
                )

    # Pastikan setiap product_url hanya muncul sekali.
    unique_records = {
        record["product_url"]: record
        for record in valid_records
    }

    valid_records = list(unique_records.values())

    save_json(
        OUTPUT_DIR / "books.json",
        valid_records,
    )

    save_json(
        OUTPUT_DIR / "errors.json",
        invalid_records,
    )

    duration_seconds = round(
        time.perf_counter() - start_clock,
        3,
    )

    finished_at = datetime.now(timezone.utc)

    run_report = {
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": duration_seconds,
        "catalogue_pages_processed": (
            RUN_METRICS["catalogue_pages_processed"]
        ),
        "discovered_books": len(books),
        "detail_pages_processed": detail_pages,
        "pages_fetched": RUN_METRICS["pages_fetched"],
        "cache_hits": RUN_METRICS["cache_hits"],
        "valid_records": len(valid_records),
        "invalid_records": len(invalid_records),
        "failed_pages": len(
            RUN_METRICS["failed_page_urls"]
        ),
        "failed_page_urls": sorted(
            RUN_METRICS["failed_page_urls"]
        ),
    }

    save_json(
        OUTPUT_DIR / "run-report.json",
        run_report,
    )

    print()
    print(f"detail_pages={detail_pages}")
    print(f"valid_records={len(valid_records)}")
    print(f"invalid_records={len(invalid_records)}")
    print(
        "failed_pages="
        f"{run_report['failed_pages']}"
    )
    print(f"duration_seconds={duration_seconds}")
    print(f"books_json={OUTPUT_DIR / 'books.json'}")
    print(f"errors_json={OUTPUT_DIR / 'errors.json'}")
    print(
        f"run_report={OUTPUT_DIR / 'run-report.json'}"
    )


if __name__ == "__main__":
    main()
