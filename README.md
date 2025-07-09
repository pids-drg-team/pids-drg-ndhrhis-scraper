Here’s the **updated project documentation** with the addition of the new file `aggregate.ipynb`, which consolidates all municipality CSVs into one standardized output format (`Final.csv`) based on `Sample.csv`.

---

# 🩺 NDHRHIS Health Workforce Data Scraper

This project automates the **extraction** and **aggregation** of health workforce data from the [NDHRHIS](https://ndhrhis.doh.gov.ph) system of the Philippine Department of Health.

It scrapes tabular data per year across multiple administrative levels and standardizes all outputs into a single, final CSV file.

---

## 📁 Folder Structure

```
project-root/
├── uploaded_html/      # Input HTML files per year (nationwide view)
├── output_csv/         # Output per year, region, province, and municipality
│   └── 2023/
│       └── <REGION>/
│           └── <REGION>.csv/
│           └── <PROVINCE>/
│               └── <PROVINCE>.csv/
│               └── <MUNICIPALITY>/
│                   └── <MUNICIPALITY>.csv/
├── Sample.csv          # Template format for final aggregated CSV
├── Final.csv           # Output: all municipalities combined
├── main.ipynb          # Scraper: collects data into output_csv/
└── aggregate.ipynb     # Aggregator: merges CSVs into Final.csv
```

---

## ⚙️ Configuration

```python
BASE_URL = "https://ndhrhis.doh.gov.ph"
HTML_DIR = "uploaded_html"
OUT_DIR = "output_csv"
```

### `YEAR_CONFIG`

Specifies year-specific dropdown metadata required by NDHRHIS:

```python
YEAR_CONFIG = {
    2024: ('02', 'As of December 31, 2024', '2025-01-03'),
    ...
    2017: ('03', 'As of December 31, 2017 - Third set of test data', '2018-06-10'),
}
```

---

## 🕸️ Web Scraping Logic (`main.ipynb`)

This is the core scraper. It:

1. **Loads** the nationwide HTML per year (`Distribution-Nationwide {year}.html`)
2. **Extracts dropdown values** for regions → provinces → municipalities
3. **Simulates POST requests** per level using those dropdowns
4. **Parses tables** into DataFrames and saves them as:

```
output_csv/{year}/{region}/{province}/{municipality}/{municipality}.csv
```

Each CSV file contains health workforce counts (rows: facilities, columns: occupation types).

---

## 📊 Aggregation Script (`aggregate.ipynb`)

This notebook loads all `*.csv` files under `output_csv/` and standardizes their structure using `Sample.csv` as the schema.

### ❗ Purpose

- **Merges all municipality-level CSVs** into a single final file: `Final.csv`
- Adds columns: `Year`, `Region`, `Province`, and `Municipality` from folder paths
- Ensures column consistency across all datasets

---

## 🚀 Parallel Execution (Scraper)

`main.ipynb` uses:

```python
with ThreadPoolExecutor(max_workers=8) as executor:
```

All years are processed in parallel for speed.

---

## ✅ Output

### Final Deliverables:

- Per-municipality CSVs: `output_csv/{year}/{region}/{province}/{municipality}.csv`
- Merged Final CSV: `Final.csv`

---

## 📌 Notes & Limitations

- Only **December reports** are extracted per year.
- Municipality requests may occasionally fail due to NDHRHIS server errors.
- Final aggregation assumes column consistency as defined by `Sample.csv`.
