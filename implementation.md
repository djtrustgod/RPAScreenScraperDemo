# Implementation Details

This document provides technical details about the NUFORC RPA Screen Scraper implementation.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        scraper.py                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ State        │  │ Browser      │  │ Data                 │  │
│  │ Management   │  │ Automation   │  │ Processing           │  │
│  │              │  │              │  │                      │  │
│  │ load_state() │  │ Playwright   │  │ extract_table_data() │  │
│  │ save_state() │  │ Chromium     │  │ save_to_csv()        │  │
│  │ clear_state()│  │ Headless     │  │ pandas DataFrame     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        output/                                  │
│  ┌─────────────────────────┐  ┌──────────────────────────────┐ │
│  │ nuforc_ca_reports.csv   │  │ .scraper_state.json          │ │
│  │ (Final output)          │  │ (Checkpoint for recovery)    │ │
│  └─────────────────────────┘  └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Browser Automation | Playwright | Navigate JavaScript-rendered pages |
| Browser Engine | Chromium (headless) | Render DataTables content |
| Data Processing | pandas | CSV export and data manipulation |
| State Persistence | JSON | Crash recovery checkpoints |

## Why Playwright?

The NUFORC website uses **DataTables** (jQuery plugin) for pagination, which loads data dynamically via JavaScript. Simple HTTP requests (requests, BeautifulSoup) cannot execute JavaScript, making browser automation necessary.

**Playwright advantages over Selenium:**
- Faster execution with auto-wait capabilities
- Better async support
- Built-in timeout handling
- Modern API design

## Key Implementation Details

### 1. Browser Context Configuration

```python
browser = p.chromium.launch(headless=True)
context = browser.new_context(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."
)
```

- **Headless mode**: No visible browser window, faster execution
- **Custom user agent**: Mimics real browser to avoid detection

### 2. Table Data Extraction

```python
def extract_table_data(page):
    page.wait_for_selector("table#table_1 tbody tr", timeout=30000)
    table_rows = page.query_selector_all("table#table_1 tbody tr")
    
    for row in table_rows:
        cells = row.query_selector_all("td")
        # Extract 9 columns from each row
```

- Waits for table to fully render before extraction
- Uses CSS selectors to target DataTables structure
- Handles variable number of cells gracefully

### 3. Pagination Navigation

```python
next_button = page.query_selector("a.paginate_button.next:not(.disabled)")
if next_button:
    next_button.click()
    page.wait_for_load_state("networkidle")
```

- Detects disabled state to know when last page reached
- Waits for network idle after click to ensure data loads

### 4. Crash Recovery System

**State file structure** (`output/.scraper_state.json`):
```json
{
    "last_page": 30,
    "total_records": 3000
}
```

**Recovery flow:**
1. On startup, check for existing state file
2. If found, navigate to `last_page + 1`
3. Append new data to existing CSV
4. Update state file every `SAVE_INTERVAL` pages
5. Delete state file on successful completion

### 5. Rate Limiting

```python
delay = random.uniform(MIN_DELAY, MAX_DELAY)
time.sleep(delay)
```

- Random delays between 1-2 seconds
- Prevents server overload
- Reduces risk of IP blocking

## Data Flow

```
1. Launch Browser
       │
       ▼
2. Navigate to NUFORC URL
       │
       ▼
3. Wait for DataTable to Load
       │
       ▼
4. Extract Current Page Data ◄────┐
       │                          │
       ▼                          │
5. Append to Buffer               │
       │                          │
       ▼                          │
6. Page % 10 == 0?                │
       │                          │
   ┌───┴───┐                      │
   Yes     No                     │
   │       │                      │
   ▼       └──────────────────────┤
7. Save CSV + State               │
       │                          │
       ▼                          │
8. More Pages? ───────────────────┘
       │
       No
       │
       ▼
9. Save Final Batch
       │
       ▼
10. Clear State File
       │
       ▼
11. Close Browser
```

## Error Handling

| Error Type | Handling Strategy |
|------------|-------------------|
| Page timeout | Save progress, raise exception for retry |
| Network error | Playwright auto-retries, then fails gracefully |
| Missing elements | Skip row, continue scraping |
| Browser crash | State file preserves progress for resume |

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Records per page | 100 |
| Delay between pages | 1-2 seconds |
| Checkpoint interval | Every 10 pages (1,000 records) |
| Estimated time for 17,000 records | ~30-40 minutes |
| Memory usage | Low (batch writes to CSV) |

## Extending the Scraper

### Scrape Different States

Change the URL parameter:
```python
BASE_URL = "https://nuforc.org/subndx/?id=lNY"  # New York
BASE_URL = "https://nuforc.org/subndx/?id=lTX"  # Texas
```

### Add Detail Page Scraping

Each row links to a detailed report. To capture full details:
```python
link = cells[0].query_selector("a")
detail_url = link.get_attribute("href")
# Navigate to detail_url and extract additional fields
```

### Export to Different Formats

Replace pandas CSV export:
```python
# Excel
df.to_excel("output/nuforc_ca_reports.xlsx", index=False)

# JSON
df.to_json("output/nuforc_ca_reports.json", orient="records")

# SQLite
import sqlite3
conn = sqlite3.connect("output/nuforc.db")
df.to_sql("sightings", conn, if_exists="append", index=False)
```

## Troubleshooting

### Browser Not Found
```
playwright._impl._errors.Error: Executable doesn't exist
```
**Solution:** Run `playwright install`

### Timeout Errors
```
TimeoutError: Timeout 30000ms exceeded
```
**Solution:** Increase timeout values or check network connectivity

### Empty CSV
**Solution:** Check if state file exists with partial progress, delete to start fresh
