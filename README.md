# NUFORC UFO Sightings RPA Screen Scraper

A Python-based RPA (Robotic Process Automation) screen scraper that extracts UFO sighting reports from the [National UFO Reporting Center (NUFORC)](https://nuforc.org/) database and exports them to CSV format.

## Features

- **Automated browser navigation** using Playwright for JavaScript-rendered content
- **Multi-page scraping** through DataTables pagination (17,000+ records)
- **Crash recovery** with incremental saves every 10 pages
- **Rate limiting** to avoid overwhelming the server
- **CSV export** with all report fields

## Data Extracted

| Field | Description |
|-------|-------------|
| Status | Report status (Open, Open .) |
| Date_Time | Sighting date and time |
| City | City of sighting |
| State | State/Province code |
| Country | Country (USA, Canada, etc.) |
| Shape | UFO shape (Orb, Triangle, Light, etc.) |
| Summary | Brief description of the sighting |
| Has_Media | Media attachment indicator |
| Explanation | Possible explanation if provided |

## Requirements

- Python 3.10+
- Playwright
- pandas

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/djtrustgod/RPAScreenScraperDemo.git
   cd RPAScreenScraperDemo
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Playwright browsers:
   ```bash
   playwright install
   ```

## Usage

Run the scraper:
```bash
python scraper.py
```

The scraper will:
1. Navigate to the NUFORC California sightings page
2. Extract data from each page (100 records per page)
3. Save checkpoints every 10 pages to `output/.scraper_state.json`
4. Export all data to `output/nuforc_ca_reports.csv`

### Resume After Interruption

If the scraper is interrupted, simply run it again:
```bash
python scraper.py
```

It will automatically resume from the last checkpoint.

### Clear State and Start Fresh

Delete the state file to start from the beginning:
```bash
del output\.scraper_state.json  # Windows
rm output/.scraper_state.json   # Linux/Mac
```

## Output

- **CSV File**: `output/nuforc_ca_reports.csv`
- **State File**: `output/.scraper_state.json` (deleted on successful completion)

## Configuration

Edit the constants in `scraper.py` to customize:

```python
BASE_URL = "https://nuforc.org/subndx/?id=lCA"  # Change state ID for other states
SAVE_INTERVAL = 10  # Save every N pages
MIN_DELAY = 1.0     # Minimum delay between pages (seconds)
MAX_DELAY = 2.0     # Maximum delay between pages (seconds)
```

## License

MIT License
