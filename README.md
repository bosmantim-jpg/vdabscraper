# VDAB Job Scraper

A Python web scraper for VDAB (Flemish employment service) job listings with a focus on credit-related positions.

**GitHub Repository:** https://github.com/bosmantim-jpg/vdabscraper

## Features

- **Pagination**: Automatically traverses all pages of search results
- **Incremental scraping**: Tracks already-processed jobs to avoid re-scraping on subsequent runs
- **Structured data extraction**: Pulls job title, company, location, salary, language requirements, and job description
- **Rate limiting**: Respects server load with random delays between requests
- **Markdown output**: Saves each job posting as a markdown file ready for AI processing

## Setup

### Prerequisites
- Python 3.9+
- Playwright installed and configured

### Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

## Usage

### First run - scrape all jobs
```bash
python scraper.py
```

### Subsequent runs - only new jobs are scraped
```bash
python scraper.py
```

The script automatically skips job IDs that have already been processed.

## Output

### Directory Structure
```
jobs/
  ├── 73911887.md    # Job posting as markdown
  ├── 73956905.md
  └── ... (one file per job)

processed.json       # Set of already-processed job IDs (auto-maintained)
```

### Markdown Format

Each job file follows this structure:

```markdown
# {job_title}

**Bedrijf:** {company_name}
**Locatie:** {location}
**Contract:** {contract_type}
**Verloning:** {salary_range}
**Referentie:** {job_id}

## Taalvereisten

| Taal | Niveau | Vereist/Gewenst |
|------|--------|-----------------|
| {language} | {level} | {status} |

## Functiebeschrijving

{job_description}

---
*Bron: {job_url}*
*Gescraped: {timestamp}*
```

## Behavior

### Search Criteria
- Keyword: "credit"
- Work circuit: 8 (credit-related roles)
- Sort order: default (relevance/date)

### Scraping Flow
1. Fetch listing page (with pagination)
2. Wait for job links to load
3. Extract all job URLs from the current page
4. For each new job ID:
   - Navigate to job detail page
   - Extract structured data (title, company, location, salary, languages, description)
   - Save as markdown
   - Record job ID in processed.json
5. Move to next page with random 3-7 second delay
6. Stop when no new jobs are found

### Rate Limiting
- 2-5 second random delay between individual job detail scrapes
- 3-7 second random delay between pagination pages
- Uses `domcontentloaded` and `networkidle` waits to reduce load

### Error Handling
- Missing fields are marked as `[MISSING]`
- Extraction failures are silently handled - the script continues rather than crashing
- Failed network requests to individual jobs are logged but don't stop the scraper

## Data Quality Notes

### Extracted Fields

| Field | Quality | Notes |
|-------|---------|-------|
| **Title** | ✓ Good | Usually accurate; filtered to skip site navigation headers |
| **Company** | ✓ Good | Whitespace-collapsed; some inline markup may remain |
| **Location** | ⚠ Fair | Often shows "VDAB-locaties" (generic); city may be in description |
| **Salary** | ⚠ Fair | Regex extraction; some jobs have complex salary text |
| **Languages** | ~ Poor | Regex-based extraction is limited; many jobs show `[MISSING]` |
| **Description** | ~ Poor | Full page text content; includes navigation and sidebars |

### Known Limitations

1. **Language requirements parsing**: The current regex is basic and misses many language entries. The language requirements section is often marked `[MISSING]` even when languages are mentioned in the description.

2. **Description quality**: The description field contains the full page text content, including navigation, sidebars, and UI elements. Use the markdown files as AI-friendly input; the AI can extract the actual job description from the noise.

3. **VDAB-locaties**: Many jobs show "VDAB-locaties" instead of a specific city. The actual location is often embedded in the description text (look for city names like TURNHOUT, ANTWERP, etc.).

## Customization

To scrape a different job search, modify these constants in `scraper.py`:

```python
BASE_URL = "https://www.vdab.be/vindeenjob/vacatures"
QUERY_PARAMS = "?trefwoord=credit&arbeidscircuit=8&sort=standaard"  # Change search criteria here
```

Replace the `trefwoord` (keyword) and `arbeidscircuit` parameters as needed.

## Performance

- Typical run: ~66-88 jobs (first 5 result pages) in 3-4 minutes
- Incremental run: Skips already-processed jobs; only scrapes new listings
- Browser overhead: Playwright launches and controls a real Chromium browser

## Files

- **scraper.py** - Main scraper script
- **requirements.txt** - Python dependencies
- **processed.json** - Auto-generated; tracks processed job IDs
- **jobs/** - Auto-generated; output markdown directory

## Troubleshooting

**Q: The scraper hangs on a page**
A: Playwright has timeouts built in. If a page takes too long, the script moves on and logs errors.

**Q: Some jobs show `[MISSING]` for all fields**
A: This happens if the page structure doesn't match our selectors. The HTML may have changed; adjust the CSS selectors in `extract_job_details()`.

**Q: How do I feed these to an LLM?**
A: The markdown files are designed to be AI-friendly. You can:
- Read them into your LLM's context
- Use a RAG/indexing pipeline
- Batch-process them through an API
- Use as few-shot examples for structured extraction

## Future Improvements

- [ ] Better language requirement extraction (structured parsing of language tables)
- [ ] Improve job description extraction (extract from main content only, not full page)
- [ ] Add support for multiple search criteria
- [ ] Add export formats (JSON, CSV)
- [ ] Implement retry logic for failed jobs
- [ ] Add logging to file instead of just stdout

## License

This scraper is for educational and research purposes. Respect VDAB's Terms of Service and robots.txt.
