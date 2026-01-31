"""
NUFORC UFO Sightings RPA Screen Scraper
Extracts data from multi-page DataTables at https://nuforc.org/subndx/?id=lCA
and exports to CSV with incremental saves and crash recovery.
"""

import json
import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import pandas as pd


# Configuration
BASE_URL = "https://nuforc.org/subndx/?id=lCA"
OUTPUT_DIR = Path("output")
CSV_FILE = OUTPUT_DIR / "nuforc_ca_reports.csv"
STATE_FILE = OUTPUT_DIR / ".scraper_state.json"
SAVE_INTERVAL = 10  # Save every N pages
MIN_DELAY = 1.0  # Minimum delay between pages (seconds)
MAX_DELAY = 2.0  # Maximum delay between pages (seconds)


def load_state():
    """Load scraper state from checkpoint file."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_page": 0, "total_records": 0}


def save_state(state):
    """Save scraper state to checkpoint file."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def clear_state():
    """Clear the state file after successful completion."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def extract_table_data(page):
    """Extract all rows from the current page's data table."""
    rows = []
    
    # Wait for table to be fully loaded
    page.wait_for_selector("table#table_1 tbody tr", timeout=30000)
    
    # Get all table rows
    table_rows = page.query_selector_all("table#table_1 tbody tr")
    
    for row in table_rows:
        cells = row.query_selector_all("td")
        if len(cells) >= 9:
            row_data = {
                "Status": cells[0].inner_text().strip(),
                "Date_Time": cells[1].inner_text().strip(),
                "City": cells[2].inner_text().strip(),
                "State": cells[3].inner_text().strip(),
                "Country": cells[4].inner_text().strip(),
                "Shape": cells[5].inner_text().strip(),
                "Summary": cells[6].inner_text().strip(),
                "Has_Media": cells[7].inner_text().strip(),
                "Explanation": cells[8].inner_text().strip(),
            }
            rows.append(row_data)
    
    return rows


def get_pagination_info(page):
    """Get current page info and total pages from DataTables."""
    try:
        info_text = page.query_selector("div#table_1_info").inner_text()
        # Parse "Showing 1 to 100 of 17,056 entries"
        parts = info_text.split()
        total_entries = int(parts[-2].replace(",", ""))
        entries_per_page = 100
        total_pages = (total_entries + entries_per_page - 1) // entries_per_page
        return total_pages, total_entries
    except Exception as e:
        print(f"Warning: Could not parse pagination info: {e}")
        return None, None


def navigate_to_page(page, target_page):
    """Navigate to a specific page number in DataTables."""
    if target_page == 1:
        return True
    
    # Click the specific page number if visible, otherwise use navigation
    try:
        # First, try clicking the page number directly
        page_button = page.query_selector(f"a.paginate_button:has-text('{target_page}')")
        if page_button:
            page_button.click()
            page.wait_for_load_state("networkidle")
            time.sleep(0.5)
            return True
        
        # If page not visible, navigate using Next button repeatedly
        current_page = 1
        while current_page < target_page:
            next_button = page.query_selector("a.paginate_button.next:not(.disabled)")
            if next_button:
                next_button.click()
                page.wait_for_load_state("networkidle")
                time.sleep(0.3)
                current_page += 1
            else:
                return False
        return True
    except Exception as e:
        print(f"Error navigating to page {target_page}: {e}")
        return False


def save_to_csv(data, append=False):
    """Save data to CSV file."""
    df = pd.DataFrame(data)
    
    if append and CSV_FILE.exists():
        df.to_csv(CSV_FILE, mode='a', header=False, index=False, encoding='utf-8')
    else:
        df.to_csv(CSV_FILE, index=False, encoding='utf-8')


def scrape_nuforc():
    """Main scraping function with crash recovery."""
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Load previous state if exists
    state = load_state()
    start_page = state["last_page"] + 1
    
    if start_page > 1:
        print(f"Resuming from page {start_page} (previously scraped {state['total_records']} records)")
    
    all_data = []
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # Navigate to the NUFORC page
            print(f"Navigating to {BASE_URL}...")
            page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
            
            # Wait for DataTables to initialize
            page.wait_for_selector("table#table_1", timeout=30000)
            time.sleep(2)  # Extra wait for JS to fully load
            
            # Get pagination info
            total_pages, total_entries = get_pagination_info(page)
            if total_pages:
                print(f"Found {total_entries:,} entries across {total_pages} pages")
            else:
                print("Could not determine total pages, will scrape until no more data")
                total_pages = 999  # Fallback
            
            # If resuming, navigate to start page
            if start_page > 1:
                print(f"Navigating to page {start_page}...")
                if not navigate_to_page(page, start_page):
                    print(f"Failed to navigate to page {start_page}")
                    return
            
            current_page = start_page
            
            while current_page <= total_pages:
                try:
                    print(f"Scraping page {current_page}/{total_pages}...")
                    
                    # Extract data from current page
                    page_data = extract_table_data(page)
                    all_data.extend(page_data)
                    
                    print(f"  Extracted {len(page_data)} records (total: {len(all_data) + state['total_records']})")
                    
                    # Incremental save every SAVE_INTERVAL pages
                    if current_page % SAVE_INTERVAL == 0:
                        print(f"  Saving checkpoint at page {current_page}...")
                        save_to_csv(all_data, append=(start_page > 1 or current_page > SAVE_INTERVAL))
                        state["last_page"] = current_page
                        state["total_records"] += len(all_data)
                        save_state(state)
                        all_data = []  # Clear buffer after saving
                    
                    # Check if we're on the last page
                    if current_page >= total_pages:
                        break
                    
                    # Click Next button
                    next_button = page.query_selector("a.paginate_button.next:not(.disabled)")
                    if not next_button:
                        print("No more pages available (Next button disabled)")
                        break
                    
                    next_button.click()
                    page.wait_for_load_state("networkidle")
                    
                    # Rate limiting with random delay
                    delay = random.uniform(MIN_DELAY, MAX_DELAY)
                    time.sleep(delay)
                    
                    current_page += 1
                    
                except PlaywrightTimeout as e:
                    print(f"Timeout on page {current_page}: {e}")
                    print("Saving current progress and retrying...")
                    if all_data:
                        save_to_csv(all_data, append=(start_page > 1 or current_page > SAVE_INTERVAL))
                        state["last_page"] = current_page - 1
                        state["total_records"] += len(all_data)
                        save_state(state)
                    raise
            
            # Save any remaining data
            if all_data:
                print("Saving final batch...")
                save_to_csv(all_data, append=(start_page > 1 or current_page > SAVE_INTERVAL))
                state["total_records"] += len(all_data)
            
            # Clear state file on successful completion
            clear_state()
            
            print(f"\n✅ Scraping complete!")
            print(f"   Total records scraped: {state['total_records']}")
            print(f"   Output file: {CSV_FILE.absolute()}")
            
        except Exception as e:
            print(f"\n❌ Error during scraping: {e}")
            print(f"   Progress saved. Run again to resume from page {state['last_page'] + 1}")
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    scrape_nuforc()
