# 🩺 NDHRHIS Health Workforce Data Scraper

This project automates the **extraction** and **aggregation** of health workforce data from the [NDHRHIS](https://ndhrhis.doh.gov.ph) system of the Philippine Department of Health.

It scrapes tabular data per year across multiple administrative levels and standardizes all outputs into final CSV files for analysis.

---

## 📁 Folder Structure

```
project-root/
├── uploaded_html/          # Input HTML files per year (ownership/“E” view; used by scrape_ownership)
├── complete_html/          # Input HTML files per year (A–E views; used by scrape_complete)
├── output_csv/             # Ownership-only outputs per year, region, province, municipality
│   └── 2023/
│       └── <REGION>/
│           ├── <REGION>.csv
│           └── <PROVINCE>/
│               ├── <PROVINCE>.csv
│               └── <MUNICIPALITY>/
│                   └── <MUNICIPALITY>.csv
├── complete_csv/           # A–E category outputs in TABLE-letter files
│   └── 2023/
│       └── <REGION>/
│           ├── <REGION>_TABLE_A.csv … _TABLE_E.csv
│           └── <PROVINCE>/
│               ├── <PROVINCE>_TABLE_A.csv … _TABLE_E.csv
│               └── <MUNICIPALITY>/
│                   ├── <MUNICIPALITY>_TABLE_A.csv … _TABLE_E.csv
├── Sample.csv              # Template schema for the ownership aggregator
├── Final_with_dupes.csv    # Aggregated (ownership) with duplicated labels filled
├── Final_with_NA.csv       # Aggregated (ownership) using "N/A" for non-applicable levels
├── Final_dirty.csv         # Aggregated (ownership) with zero cleaning of labels
├── requirements.txt
├── scrape_ownership.ipynb  # Formerly main.ipynb — scrapes “Ownership” view (single table set)
├── aggregate_ownership.ipynb # Formerly aggregate.ipynb — merges ownership CSVs
└── scrape_complete.ipynb   # Formerly complete.ipynb — scrapes all A–E category tables
```

---

## ⚙️ Configuration

Common constants (used in the notebooks):

```python
BASE_URL = "https://ndhrhis.doh.gov.ph"

# For ownership-only scrape
HTML_DIR = "uploaded_html"
OUT_DIR  = "output_csv"

# For complete A–E scrape
HTML_DIR = "complete_html"
OUT_DIR  = "complete_csv"
```

### `YEAR_CONFIG`

Parsed from the NDHRHIS archive listings. **Only December** releases per year are included.

```python
YEAR_CONFIG = {
    2024: ('02', 'As of December 31, 2024', '2025-01-03'),
    2023: ('02', 'As of December 2023', '2024-01-02'),
    2022: ('02', 'As of December 2022', '2023-01-04'),
    2021: ('03', 'As of December 2021', '2022-01-03'),
    2020: ('01', 'As of December 31, 2020', '2020-07-22'),
    2019: ('01', 'As Of December 31, 2019', '2020-01-24'),  # note capital “Of”
    2018: ('01', 'As of December 31, 2018', '2018-09-07'),
    2017: ('03', 'As of December 31, 2017 - Third set of test data', '2018-06-10'),
}
```

---

## 🕸️ Scrapers

### 1) `scrape_ownership.ipynb` (formerly `main.ipynb`)

Scrapes the **Ownership** / single-table view (report code `sbrep=E`) across Region → Province → Municipality.

**Key behaviors**

- Loads nationwide HTML (`uploaded_html/Distribution-Nationwide {year}.html`)
- Extracts dropdown values for Region/Province/Municipality
- Simulates POST for each level and **saves every detected table** as CSV
- Output path pattern:

  ```
  output_csv/{year}/{region}/{province}/{municipality}/{municipality}.csv
  ```

- Parallelized across years:

  ```python
  from concurrent.futures import ThreadPoolExecutor, as_completed
  with ThreadPoolExecutor(max_workers=8) as ex:
      ...
  ```

**Install & run**

```bash
# In Jupyter cell at the top of the notebook:
!pip install -r requirements.txt
# Then run all cells
```

---

### 2) `scrape_complete.ipynb` (formerly `complete.ipynb`)

Scrapes **all five category tables** A–E in one pass per place (report code `sbrep=A B C D E`).
Each table is saved separately, suffixed by `_TABLE_<LETTER>.csv`.

**Table detection**

- Only tables with class `RepT` and IDs like `treportA`…`treportE` are saved.
- Output filename pattern:

  ```
  <PLACE>_TABLE_A.csv … _TABLE_E.csv
  ```

**Install & run**

```bash
# In Jupyter cell at the top of the notebook:
!pip install -r requirements.txt
# Then run all cells
```

---

## 📊 Ownership Aggregation (`aggregate_ownership.ipynb`)

Merges all CSVs from `output_csv/` into three final variants. Uses `Sample.csv` to enforce column order and presence.

**Assumptions**

- `Sample.csv` includes canonical columns:

  - Metadata: `Year`, `Region`, `Province`, `Municipality`
  - Plus data columns (e.g., occupation types, `Ownership`, etc.)

- Any missing data columns (relative to `Sample.csv`) are added with `0`.

**Outputs**

- `Final_with_dupes.csv` — fills hierarchical labels **with duplicates** where appropriate
- `Final_with_NA.csv` — uses `"N/A"` where a level doesn’t apply
- `Final_dirty.csv` — **no cleaning at all**; preserves original folder names 1:1

**Filtering**

- If an `Ownership` column exists, **rows with `Ownership == "TOTAL"` are dropped**.

**Run**
Open the notebook and run all cells. The script will:

1. Walk `output_csv/{year}/{region}/{province}/{municipality}`
2. Read `*.csv`
3. Normalize columns to `Sample.csv`
4. Write the three finals to project root

---

## 🧹 Labeling & Cleaning Rules (Ownership Aggregation)

- **Dirty mode**: exact folder names → no cleaning (good for audits/debug)
- **Clean mode**:

  - Regions: strip prefixes like `^\d{2}_-_`
  - Replace `_` with spaces
  - For `with_dupes`: repeat labels down the hierarchy where needed
  - For `with_NA`: fill non-applicable levels with `"N/A"`

---

## 🚦 Reliability & Notes

- **Only December** reports per year are targeted.
- Province/Municipality requests may intermittently fail (server-side). Scripts catch and log errors per place and continue.
- Region-level pages typically contain non-zero data; municipality pages **can** be all zeroes.
- `scrape_complete.ipynb` saves one CSV per category (A–E) for each place.
- `scrape_ownership.ipynb` saves all valid tables present on each page (ownership view).

---

## 🧪 Quickstart

1. Place the nationwide HTML files per year into:

- Ownership: `uploaded_html/Distribution-Nationwide {YYYY}.html`
- Complete: `complete_html/Distribution-Nationwide {YYYY}.html`

2. Scrape:

- Ownership-only: run `scrape_ownership.ipynb`
- Complete (A–E): run `scrape_complete.ipynb`

3. Aggregate (ownership):

- Run `aggregate_ownership.ipynb`
- Get `Final_with_dupes.csv`, `Final_with_NA.csv`, `Final_dirty.csv`

---

## 🔧 Requirements

Install from the notebooks (first cell):

```bash
!pip install -r requirements.txt
```

Typical contents:

- `requests`
- `beautifulsoup4`
- `lxml`
- `pandas`

---

## 🧰 Troubleshooting

- **No tables saved**: Ensure the HTML source is the correct nationwide “Distribution” page for December of the target year.
- **Mismatched columns**: Update `Sample.csv` to reflect the canonical schema you want in the final outputs.
- **Weird names in finals**: Use `Final_dirty.csv` to inspect raw folder labels; adjust cleaning in `aggregate_ownership.ipynb` if needed.
- **Intermittent 500/timeout**: Re-run; the scrapers log and continue past failures.

---

## 🗂️ Changelog (since prior README)

- **Renamed notebooks**

  - `main.ipynb` → **`scrape_ownership.ipynb`** (ownership-only scrape)
  - `aggregate.ipynb` → **`aggregate_ownership.ipynb`** (ownership aggregator)
  - `complete.ipynb` → **`scrape_complete.ipynb`** (A–E categories scrape)

- **New aggregation variants**

  - Added **`Final_dirty.csv`** (no label cleaning)
  - Split outputs into **`Final_with_dupes.csv`** and **`Final_with_NA.csv`**

- **Complete scrape outputs**

  - Introduced **`complete_html/`** and **`complete_csv/`**
  - Saves one CSV per category letter: `*_TABLE_A.csv … *_TABLE_E.csv`

- **Stability & parsing**

  - More robust dropdown extraction and table parsing
  - Consistent filename sanitization and per-level directory structure

---

## 📜 License & Attribution

This project interacts with NDHRHIS public-facing pages to collect tabular data for research and policy analysis. Please follow NDHRHIS/DOH terms of use and attribute appropriately in downstream outputs.
