# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VDAB Job Scraper is a Python web scraper that automatically fetches job postings from the Flemish employment service (VDAB). It extracts structured job data (title, company, location, salary, language requirements) and saves each posting as a markdown file suitable for AI processing. The scraper is designed for incremental re-runs - it tracks already-processed jobs to avoid redundant scraping.

## Setup & Development

### Installation
```bash
pip install -r requirements.txt
playwright install chromium
```

### Running the Scraper
```bash
# First run - scrapes all jobs
python scraper.py

# Subsequent runs - only new jobs are processed
python scraper.py
```

### Testing Individual Components
```bash
# Test Playwright + page loading
python test_playwright.py

# Test detail page extraction
python test_detail.py

# Test single job extraction
python test_single_job.py
```

## Architecture

### High-Level Structure

The scraper operates in a simple linear pipeline:

1. **Listing page fetcher** (`scrape_page`): Navigates to VDAB search results with pagination
2. **Job URL extractor**: Identifies all job posting links on the listing page
3. **Detail page scraper** (`extract_job_details`): Fetches and parses individual job postings
4. **Data extractor**: Pulls structured fields (title, company, location, salary, languages, description)
5. **Markdown writer** (`save_job_markdown`): Formats and saves output
6. **State manager**: Tracks processed job IDs in `processed.json`

### Directory Layout
```
.
├── scraper.py           # Main scraper entry point
├── requirements.txt     # Python dependencies (playwright>=1.40.0)
├── processed.json       # Auto-generated state file (JSON list of job IDs)
├── jobs/                # Auto-generated output directory
│   ├── 73911887.md
│   ├── 73956905.md
│   └── ... (one .md file per job)
├── README.md            # Full documentation
├── CLAUDE.md            # This file
└── test_*.py            # Test/debug scripts (can be deleted)
```

### Key Dependencies & Technologies

- **Playwright**: Headless browser automation. Used because VDAB's job pages are JavaScript-rendered SPAs; `requests` + BeautifulSoup won't work.
- **asyncio**: Async Python for non-blocking I/O during browser operations
- **re (regex)**: Text parsing for salary ranges, language extraction, and field cleanup

### Important Architectural Notes

**Why Playwright?**
The VDAB website renders job listings dynamically with JavaScript. Playwright drives a real Chromium browser, executes the JS, and waits for content to load. It's slower than HTTP requests but necessary here.

**Wait strategies used:**
- `domcontentloaded`: Fast initial wait for the HTML to render
- `networkidle`: Falls back if JS makes additional network requests; timeout gracefully if it takes too long
- `wait_for_selector`: Ensures specific job content is present before scraping

**Rate limiting:**
- 2-5 second random delay between job detail pages
- 3-7 second random delay between listing pages
- Helps avoid overloading VDAB's servers and reduces chance of IP blocking

**State management:**
- `processed.json` is a simple JSON list of job IDs
- Written after every successful job scrape (crash-safe design)
- Allows resuming partial runs without re-scraping

## Common Tasks

### Scrape a new search query
Edit `scraper.py` line 11-12:
```python
QUERY_PARAMS = "?trefwoord={YOUR_KEYWORD}&arbeidscircuit={CIRCUIT_CODE}&sort=standaard"
```

### Debug a specific job
Use `test_single_job.py` with the job URL. Modify the `job_url` variable to test individual extraction logic.

### Check extraction quality
Review a few files in `jobs/` directory. Fields marked `[MISSING]` indicate where selectors or regex patterns failed to find data.

### Reset and re-scrape everything
```bash
rm -f processed.json
rm -rf jobs/*
python scraper.py
```

## Important Notes

- **VDAB's robots.txt** blocks `/vacatures/` (old paths) but the site is accessible. Scraping is done respectfully with rate limiting.
- **Language requirement extraction** is weak. Current regex is basic; many jobs show `[MISSING]` even though languages are mentioned in the description.
- **Job descriptions** include full page text (navigation, sidebars). AI processing should filter to actual job description content.
- **Location field** often shows "VDAB-locaties"; real city names appear in the description text or company info section.
