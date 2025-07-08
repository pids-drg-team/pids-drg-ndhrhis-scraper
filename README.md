Here is the complete `.md` documentation for your script:

---

# NDHRHIS Health Workforce Data Scraper

This Python script automates the extraction of **health workforce distribution tables** from the [National Database of Selected Human Resources for Health (NDHRHIS)](https://ndhrhis.doh.gov.ph) system of the **Philippine Department of Health**.

It processes the HTML structure across four hierarchical levels:

- **Nationwide (preloaded input)**
- **Region**
- **Province**
- **Municipality**

All relevant `<table>` elements are parsed from each page and saved as `.csv` files.

---

## 📁 Folder Structure

- `uploaded_html/` – Input folder containing saved nationwide HTML pages (`Distribution-Nationwide {year}.html`)
- `output_csv/` – Output folder where all parsed CSVs will be stored in subdirectories per year, region, province, and municipality.

---

## ⚙️ Configuration

```python
BASE_URL = "https://ndhrhis.doh.gov.ph"
HTML_DIR = "uploaded_html"
OUT_DIR = "output_csv"
```

### `YEAR_CONFIG`

Defines configuration per year based on manually parsed NDHRHIS metadata.

```python
YEAR_CONFIG = {
    2024: ('02', 'As of December 31, 2024', '2025-01-03'),
    ...
    2019: ('01', 'As Of December 31, 2019', '2020-01-24'),  # Note: "Of" capitalization
    ...
}
```

Each value is a tuple of:

- `seqn`: NDHRHIS release sequence number
- `title`: Dropdown label string
- `gdate`: Data publication date (for URL construction)

### HTTP Headers

Defined once for all POST requests:

```python
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    ...
}
```

---

## 🔧 Functions

### `extract_dropdown_values(soup)`

Parses the `<select name="ddparams">` dropdown and returns a list of `(value, label)` tuples, excluding null or empty options.

---

### `build_post_url(level, year)`

Constructs the target POST request URL for a given administrative level (2=region, 3=province, 4=municipality) and year.

---

### `get_html_for_year(year)`

Loads the corresponding pre-saved HTML file for the nationwide view of a given year.

---

### `submit_and_parse(session, url, ddvalue)`

Sends a simulated form POST request using the given dropdown value (`ddvalue`) and returns the parsed HTML response.

---

### `sanitize_filename(name)`

Cleans a string to be safe for use as a filename (removes special characters, replaces spaces with underscores).

---

### `extract_and_save_tables(soup, outdir, name, year, level)`

- Finds all `<table>` elements from the provided HTML soup.
- Converts valid tables to pandas DataFrames.
- Saves each one to `output_csv/{year}/{level}/{name}.csv`.

---

### `process_year(year)`

Main routine for processing a single year:

1. Parses the uploaded nationwide file to get regions.
2. Sends POST requests for each region to get its provinces.
3. Sends POST requests for each province to get its municipalities.
4. For each level (region, province, municipality), all valid tables are saved.

Robust `try/except` blocks ensure partial failures (e.g., one broken municipality) do not stop the entire year’s processing.

---

## 🚀 Parallel Execution

In the entry point:

```python
if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=8) as executor:
        ...
```

All configured years are processed in parallel using `ThreadPoolExecutor`.

---

## ✅ Output

All extracted tables are saved as CSVs inside `output_csv/`:

```
output_csv/
└── 2023/
    ├── ILOCOS_REGION/
    │   ├── ILOCOS_NORTE/
    │   │   └── LAOAG_CITY.csv
    │   └── PANGASINAN/
    │       └── DAGUPAN_CITY.csv
    └── CENTRAL_VISAYAS/
        └── ...
```

Each CSV file represents a full HTML `<table>` scraped from the NDHRHIS system.

---

## ⚠️ Notes & Limitations

- You **must manually download the nationwide HTML pages** and place them into `uploaded_html/` as `Distribution-Nationwide {year}.html`.
- Region and province dropdowns depend on prior levels loading correctly.
- Municipality-level requests may occasionally fail or time out — errors are logged but do not halt processing.
- Only **December listings** are used from each year (ignoring mid-year reports).
- Minor inconsistencies like `"As of"` vs `"As Of"` are handled.

---

## 🧩 Dependencies

Ensure the following packages are installed:

```bash
pip install requests beautifulsoup4 pandas lxml
```

---
