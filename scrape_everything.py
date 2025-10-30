#!/usr/bin/env python3
"""Run both NDHRHIS ownership and complete scrapers in one go."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from queue import Queue
from threading import Thread
from typing import Callable

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ----------------------------
# Configuration
# ----------------------------

BASE_URL = "https://ndhrhis.doh.gov.ph"
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

TableSaver = Callable[[BeautifulSoup, str, str, int, str], None]


@dataclass(frozen=True)
class ScrapeConfig:
    name: str
    html_dir: str
    out_dir: str
    sbrep: str
    save_tables: TableSaver
    max_workers: int = 14


# ----------------------------
# Shared helpers
# ----------------------------

def extract_dropdown_values(soup: BeautifulSoup):
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


def sanitize_filename(name: str) -> str:
    return re.sub(r"[^\w\s-]", "", name).replace(" ", "_")


def build_post_url(level: int, year: int, config: ScrapeConfig) -> str:
    seqn, title, gdate = YEAR_CONFIG[year]
    return (
        f"{BASE_URL}/system.bcall.page.php?xcrs=RPA0001b.php&prm="
        f"level={level}^year={year}^seqn={seqn}^title={title}^gdate={gdate}^"
        f"allfltr=0^prvslct=A^prvlist=^sbrep={config.sbrep}"
    )


def get_html_for_year(year: int, config: ScrapeConfig) -> BeautifulSoup:
    path = os.path.join(config.html_dir, f"Distribution-Nationwide {year}.html")
    with open(path, encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "lxml")


def submit_and_parse(session: requests.Session, url: str, ddvalue: str) -> BeautifulSoup:
    time.sleep(0.01)
    resp = session.post(url, headers=HEADERS, data={"ddparams": ddvalue, "submit": "Submit"})
    resp.raise_for_status()
    time.sleep(0.01)
    return BeautifulSoup(resp.text, "lxml")


# ----------------------------
# Table extraction variants
# ----------------------------

def save_ownership_tables(soup: BeautifulSoup, outdir: str, name: str, year: int, level: str):
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


def save_complete_tables(soup: BeautifulSoup, outdir: str, place_name: str, year: int, level: str):
    os.makedirs(outdir, exist_ok=True)
    for table in soup.find_all("table", class_="RepT"):
        table_id = table.get("id", "")
        match = re.match(r"treport([A-Z])", table_id)
        if not match:
            continue
        category_letter = match.group(1)

        rows = table.find_all("tr")
        data = [
            [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
            for row in rows
            if row.find_all(["td", "th"])
        ]
        if len(data) < 2:
            continue
        df = pd.DataFrame(data[1:], columns=data[0])
        fname = f"{sanitize_filename(place_name)}_TABLE_{category_letter}.csv"
        df.to_csv(os.path.join(outdir, fname), index=False)
        print(f"✅ Saved CSV: {year}/{level}/{fname}")


# ----------------------------
# Scraper runner
# ----------------------------

def run_scrape(config: ScrapeConfig):
    print(f"\n🚀 Starting {config.name} scrape")
    os.makedirs(config.out_dir, exist_ok=True)

    task_queue: Queue[tuple[Callable, tuple]] = Queue()

    def submit(task: Callable, *args):
        task_queue.put((task, args))

    def worker():
        while True:
            item = task_queue.get()
            if item is None:
                task_queue.task_done()
                break
            func, args = item
            try:
                func(*args)
            finally:
                task_queue.task_done()

    def process_municipality(year: int, province_dir: str, muni_val: str, muni_label: str):
        try:
            with requests.Session() as session:
                url = build_post_url(level=4, year=year, config=config)
                muni_soup = submit_and_parse(session, url, muni_val)
            muni_dir = os.path.join(province_dir, sanitize_filename(muni_label))
            config.save_tables(muni_soup, muni_dir, muni_label, year, "Municipality")
        except Exception as exc:  # pylint: disable=broad-except
            print(f"❌ [{config.name}] municipality {muni_label}: {exc}")

    def process_province(year: int, region_dir: str, province_val: str, province_label: str):
        try:
            with requests.Session() as session:
                url = build_post_url(level=3, year=year, config=config)
                province_soup = submit_and_parse(session, url, province_val)
            province_dir = os.path.join(region_dir, sanitize_filename(province_label))
            config.save_tables(province_soup, province_dir, province_label, year, "Province")

            for muni_val, muni_label in extract_dropdown_values(province_soup):
                submit(process_municipality, year, province_dir, muni_val, muni_label)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"❌ [{config.name}] province {province_label}: {exc}")

    def process_region(year: int, region_val: str, region_label: str):
        try:
            with requests.Session() as session:
                url = build_post_url(level=2, year=year, config=config)
                region_soup = submit_and_parse(session, url, region_val)
            region_dir = os.path.join(config.out_dir, str(year), sanitize_filename(region_label))
            config.save_tables(region_soup, region_dir, region_label, year, "Region")

            for province_val, province_label in extract_dropdown_values(region_soup):
                submit(process_province, year, region_dir, province_val, province_label)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"❌ [{config.name}] region {region_label}: {exc}")

    def process_year(year: int):
        try:
            print(f"\n🔍 [{config.name}] Processing year: {year}")
            entry_soup = get_html_for_year(year, config)
            for region_val, region_label in extract_dropdown_values(entry_soup):
                submit(process_region, year, region_val, region_label)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"❌ [{config.name}] could not initialize year {year}: {exc}")

    workers = [Thread(target=worker, daemon=True) for _ in range(config.max_workers)]
    for thread in workers:
        thread.start()

    for year in sorted(YEAR_CONFIG):
        process_year(year)

    task_queue.join()

    for _ in workers:
        task_queue.put(None)
    for thread in workers:
        thread.join()

    print(f"\n✅ Finished {config.name} scrape")


def main():
    configs = [
        ScrapeConfig(
            name="Ownership",
            html_dir="uploaded_html",
            out_dir="output_csv",
            sbrep="E",
            save_tables=save_ownership_tables,
        ),
        ScrapeConfig(
            name="Complete",
            html_dir="complete_html",
            out_dir="complete_csv",
            sbrep="A%20B%20C%20D%20E",
            save_tables=save_complete_tables,
        ),
    ]
    for config in configs:
        run_scrape(config)


if __name__ == "__main__":
    main()
