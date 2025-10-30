#!/usr/bin/env python3
"""Concurrent scraper for NDHRHIS ownership distribution tables."""

import os
import re
import time
from queue import Queue
from threading import Thread

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ----------------------------
# Configuration
# ----------------------------

BASE_URL = "https://ndhrhis.doh.gov.ph"
HTML_DIR = "uploaded_html"
OUT_DIR = "output_csv"
os.makedirs(OUT_DIR, exist_ok=True)

# Latest December listings per year
YEAR_CONFIG = {
    2024: ("02", "As of December 31, 2024", "2025-01-03"),
    2023: ("02", "As of December 2023", "2024-01-02"),
    2022: ("02", "As of December 2022", "2023-01-04"),
    2021: ("03", "As of December 2021", "2022-01-03"),
    2020: ("01", "As of December 31, 2020", "2020-07-22"),
    2019: ("01", "As Of December 31, 2019", "2020-01-24"),  # capital "Of"
    2018: ("01", "As of December 31, 2018", "2018-09-07"),
    2017: ("03", "As of December 31, 2017 - Third set of test data", "2018-06-10"),
}

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://ndhrhis.doh.gov.ph/RPA0001b.php",
    "Origin": "https://ndhrhis.doh.gov.ph",
    "Content-Type": "application/x-www-form-urlencoded",
}

MAX_WORKERS = 14
TASK_QUEUE: "Queue[tuple]" = Queue()


# ----------------------------
# Helpers
# ----------------------------

def extract_dropdown_values(soup: BeautifulSoup):
    """Extract all non-empty dropdown (value, label) pairs, including edge cases."""
    sel = soup.find("select", attrs={"name": "ddparams"})
    if not sel:
        return []
    options = []
    for opt in sel.find_all("option"):
        value = opt.get("value", "").strip()
        label = opt.text.strip()
        if value and label and value.lower() != "null":
            options.append((value, label))
    return options


def build_post_url(level: int, year: int) -> str:
    """Build a POST URL to request region/province/municipality for a specific year."""
    seqn, title, gdate = YEAR_CONFIG[year]
    return (
        f"{BASE_URL}/system.bcall.page.php?xcrs=RPA0001b.php&prm="
        f"level={level}^year={year}^seqn={seqn}^title={title}^gdate={gdate}^"
        "allfltr=0^prvslct=A^prvlist=^sbrep=E"
    )


def get_html_for_year(year: int) -> BeautifulSoup:
    """Load uploaded nationwide HTML file for the given year."""
    path = os.path.join(HTML_DIR, f"Distribution-Nationwide {year}.html")
    with open(path, encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "lxml")


def submit_and_parse(session: requests.Session, url: str, ddvalue: str) -> BeautifulSoup:
    """Simulate POST request with dropdown selection and parse resulting page."""
    time.sleep(0.01)
    resp = session.post(url, headers=HEADERS, data={"ddparams": ddvalue, "submit": "Submit"})
    resp.raise_for_status()
    time.sleep(0.01)
    return BeautifulSoup(resp.text, "lxml")


def sanitize_filename(name: str) -> str:
    """Clean directory and file names to avoid filesystem issues."""
    return re.sub(r"[^\w\s-]", "", name).replace(" ", "_")


def extract_and_save_tables(soup: BeautifulSoup, outdir: str, name: str, year: int, level: str):
    """Parse all valid tables from the page and save as CSVs under the specified path."""
    os.makedirs(outdir, exist_ok=True)
    tables = soup.find_all("table")
    count = 0
    for table in tables:
        rows = table.find_all("tr")
        data = [
            [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
            for row in rows
            if row.find_all(["td", "th"])
        ]
        if len(data) < 2:
            continue
        df = pd.DataFrame(data[1:], columns=data[0])
        fname = f"{sanitize_filename(name)}.csv"
        df.to_csv(os.path.join(outdir, fname), index=False)
        print(f"✅ Saved CSV: {year}/{level}/{fname}")
        count += 1
    if count == 0:
        print(f"⚠️ No valid tables found for {year}/{level}/{name}")


def submit(task, *args):
    """Enqueue a scraping task."""
    TASK_QUEUE.put((task, args))


# ----------------------------
# Concurrent processors
# ----------------------------

def process_municipality(year: int, province_dir: str, muni_val: str, muni_label: str):
    try:
        with requests.Session() as session:
            url_muni = build_post_url(level=4, year=year)
            muni_soup = submit_and_parse(session, url_muni, muni_val)
        muni_dir = os.path.join(province_dir, sanitize_filename(muni_label))
        extract_and_save_tables(muni_soup, muni_dir, muni_label, year, "Municipality")
    except Exception as exc:  # pylint: disable=broad-except
        print(f"❌ Error in municipality {muni_label}: {exc}")


def process_province(year: int, region_dir: str, province_val: str, province_label: str):
    try:
        with requests.Session() as session:
            url_prov = build_post_url(level=3, year=year)
            province_soup = submit_and_parse(session, url_prov, province_val)
        province_dir = os.path.join(region_dir, sanitize_filename(province_label))
        extract_and_save_tables(province_soup, province_dir, province_label, year, "Province")

        for muni_val, muni_label in extract_dropdown_values(province_soup):
            submit(process_municipality, year, province_dir, muni_val, muni_label)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"❌ Error in province {province_label}: {exc}")


def process_region(year: int, region_val: str, region_label: str):
    try:
        with requests.Session() as session:
            url_region = build_post_url(level=2, year=year)
            region_soup = submit_and_parse(session, url_region, region_val)
        region_dir = os.path.join(OUT_DIR, str(year), sanitize_filename(region_label))
        extract_and_save_tables(region_soup, region_dir, region_label, year, "Region")

        for province_val, province_label in extract_dropdown_values(region_soup):
            submit(process_province, year, region_dir, province_val, province_label)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"❌ Error in region {region_label}: {exc}")


def process_year(year: int):
    try:
        print(f"\n🔍 Processing year: {year}")
        entry_soup = get_html_for_year(year)
        for region_val, region_label in extract_dropdown_values(entry_soup):
            submit(process_region, year, region_val, region_label)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"❌ Could not initialize year {year}: {exc}")


# ----------------------------
# Workers
# ----------------------------

def worker():
    while True:
        item = TASK_QUEUE.get()
        if item is None:
            TASK_QUEUE.task_done()
            break
        func, args = item
        try:
            func(*args)
        finally:
            TASK_QUEUE.task_done()


def run():
    workers = [Thread(target=worker, daemon=True) for _ in range(MAX_WORKERS)]
    for thread in workers:
        thread.start()

    for year in sorted(YEAR_CONFIG):
        process_year(year)

    TASK_QUEUE.join()

    for _ in workers:
        TASK_QUEUE.put(None)
    for thread in workers:
        thread.join()


if __name__ == "__main__":
    run()
