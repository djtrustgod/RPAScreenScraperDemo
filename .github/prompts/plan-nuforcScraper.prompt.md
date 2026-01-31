## Plan: NUFORC UFO Data Multi-Page Scraper

Build a Python-based RPA screen scraper using Playwright to extract all 17,000+ UFO sighting records from the NUFORC California data table and export to CSV. Playwright is required because the site uses JavaScript-based DataTables pagination.

### Steps
1. **Create project structure** with requirements.txt containing `playwright`, `pandas`, and scraper.py as the main script.
2. **Implement browser automation** in scraper.py using Playwright to launch a headless browser, navigate to `https://nuforc.org/subndx/?id=lCA`, and wait for the DataTable to fully render.
3. **Build pagination loop** to iterate through all 171 pages by clicking the "Next" button, extracting table rows (Status, Date/Time, City, State, Country, Shape, Summary, Has Media, Explanation) after each page load.
4. **Add CSV export logic** using pandas to write scraped data in batches to output/nuforc_ca_reports.csv, handling empty fields gracefully.
5. **Implement rate limiting** with 1-2 second delays between page requests to avoid overwhelming the server and potential blocking.
6. **Add incremental saves with crash recovery** — Save scraped data to CSV every 10 pages (~1,000 records) to prevent data loss if the scraper crashes mid-run. Track progress in a state file (e.g., `output/.scraper_state.json`) containing the last successfully scraped page number. On restart, check for the state file and resume from the last checkpoint rather than starting over, appending new data to the existing partial CSV.

### Further Considerations
1. **DataTables AJAX endpoint?** Inspecting network requests might reveal a direct JSON API, which would be faster than browser automation—should I investigate this approach first?
2. **Detail page scraping?** Each row links to a full report—do you need just the table summary or full report details (would significantly increase scrape time)?
