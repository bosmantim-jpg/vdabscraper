#!/usr/bin/env python3
import asyncio
import json
import random
import time
import re
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

BASE_URL = "https://www.vdab.be/vindeenjob/vacatures"
QUERY_PARAMS = "?trefwoord=credit&arbeidscircuit=8&sort=standaard"
JOBS_DIR = Path("jobs")
PROCESSED_FILE = Path("processed.json")

def load_processed():
    """Load set of already-processed job IDs."""
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_processed(processed_ids):
    """Save processed job IDs to file."""
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(processed_ids), f, indent=2)

def ensure_jobs_dir():
    """Create jobs directory if it doesn't exist."""
    JOBS_DIR.mkdir(exist_ok=True)

def extract_job_id_from_url(url):
    """Extract job ID from detail URL (e.g., /vacatures/10040455 -> 10040455)."""
    match = re.search(r"/vacatures/(\d+)", url)
    return match.group(1) if match else None

async def extract_job_details(browser, job_url):
    """Extract job details from a job detail page."""
    page = await browser.new_page()
    page.set_default_timeout(30000)

    try:
        await page.goto(job_url, wait_until="domcontentloaded", timeout=20000)

        # Wait for job content to load
        try:
            await page.wait_for_load_state("networkidle", timeout=12000)
        except:
            pass  # Continue even if still loading

    except Exception as e:
        await page.close()
        raise

    details = {
        "url": job_url,
        "title": "[MISSING]",
        "company": "[MISSING]",
        "location": "[MISSING]",
        "salary": "[MISSING]",
        "contract_type": "[MISSING]",
        "languages": [],
        "description": "[MISSING]",
        "scraped_date": datetime.now().isoformat(),
    }

    try:
        # Extract title - get all h1s and pick the one with actual job content (not the header nav)
        h1_elems = await page.query_selector_all("h1")
        for h1 in h1_elems:
            text = (await h1.text_content()).strip()
            if text and len(text) > 5 and text != "Vind een job":  # Skip site header h1
                details["title"] = text
                break
    except Exception as e:
        pass  # Title is important but extraction may fail

    try:
        # Extract company (look for werkgever/company labels)
        company_elem = await page.query_selector("[class*='werkgever'], [class*='company'], [data-label='Werkgever']")
        if company_elem:
            company_text = (await company_elem.text_content()).strip()
            # Clean up whitespace
            company_text = ' '.join(company_text.split())[:100]  # Get first 100 chars
            details["company"] = company_text
    except Exception as e:
        pass  # Company is optional

    try:
        # Extract location
        location_elem = await page.query_selector("[class*='locatie'], [class*='location'], [aria-label*='locatie']")
        if location_elem:
            details["location"] = (await location_elem.text_content()).strip()
    except Exception as e:
        pass  # Location is optional

    try:
        # Extract salary (look for text containing "loon", "verloning", "salary", "€")
        salary_text = await page.text_content("body")
        if salary_text:
            salary_match = re.search(r"(loon|verloning|salary|salaris).*?(\d+\.?\d*\s*€|\€\s*\d+\.?\d*|\d+\s*-\s*\d+)", salary_text, re.IGNORECASE)
            if salary_match:
                details["salary"] = salary_match.group(0).strip()
    except Exception as e:
        pass  # Salary is optional

    try:
        # Extract contract type
        contract_elem = await page.query_selector("[class*='contract'], [class*='arbeidsregime']")
        if contract_elem:
            details["contract_type"] = (await contract_elem.text_content()).strip()
    except Exception as e:
        pass  # Contract type is optional

    try:
        # Extract language requirements
        # Look for section containing "taal" or "taalvereisten"
        lang_section = await page.query_selector("[class*='taal']")
        if lang_section:
            lang_text = await lang_section.text_content()
            # Parse language entries (this is a simplified approach)
            lang_entries = re.findall(r"(nederlands|engels|frans|duits|spaans|italiaans|pools|portugees).*?(a1|a2|b1|b2|c1|c2).*?(vereist|verplicht|gewenst|pluspunt)", lang_text, re.IGNORECASE)
            for lang, level, requirement in lang_entries:
                is_required = "vereist" in requirement.lower() or "verplicht" in requirement.lower()
                details["languages"].append({
                    "language": lang.capitalize(),
                    "level": level.upper(),
                    "required": is_required
                })
    except Exception as e:
        pass  # Languages are optional

    try:
        # Extract job description - look for main content areas that are NOT navigation
        # Try multiple strategies to find the actual job posting content
        desc_elem = None

        # Strategy 1: Look for elements with specific content classes
        desc_elem = await page.query_selector("[class*='vacancy-details'], [class*='job-details'], [class*='job-content'], [class*='posting-content']")

        # Strategy 2: If not found, look for main content area (skip nav/sidebar)
        if not desc_elem:
            desc_elem = await page.query_selector("main, [role='main']")

        # Strategy 3: Find the largest text block (likely the description)
        if not desc_elem:
            # Get all paragraph and section elements
            candidates = await page.query_selector_all("article, section, [class*='content']")
            if candidates:
                # Get the first substantial one
                for candidate in candidates[:5]:
                    text = await candidate.text_content()
                    if len(text.strip()) > 500:  # Must have substantial content
                        desc_elem = candidate
                        break

        if desc_elem:
            desc_text = await desc_elem.text_content()
            # Clean up excessive whitespace
            desc_text = ' '.join(desc_text.split())
            details["description"] = desc_text[:2000]  # Increased from 1000 to capture more
    except Exception as e:
        pass  # Description is optional

    await page.close()
    return details

def save_job_markdown(job_id, details):
    """Save job details as a markdown file."""
    md_content = f"""# {details['title']}

**Bedrijf:** {details['company']}
**Locatie:** {details['location']}
**Contract:** {details['contract_type']}
**Verloning:** {details['salary']}
**Referentie:** {job_id}

## Taalvereisten

"""

    if details["languages"]:
        md_content += "| Taal | Niveau | Vereist/Gewenst |\n"
        md_content += "|------|--------|------------------|\n"
        for lang_entry in details["languages"]:
            required = "Vereist" if lang_entry["required"] else "Gewenst"
            md_content += f"| {lang_entry['language']} | {lang_entry['level']} | {required} |\n"
    else:
        md_content += "*Geen taalvereisten gevonden.*\n"

    md_content += f"""

## Functiebeschrijving

{details['description']}

---
*Bron: {details['url']}*
*Gescraped: {details['scraped_date']}*
"""

    output_file = JOBS_DIR / f"{job_id}.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"  [+] Saved to {output_file}")

async def scrape_page(browser, page_num, processed_ids, all_job_urls):
    """Scrape a single listing page."""
    page = await browser.new_page()
    page.set_default_timeout(30000)

    url = f"{BASE_URL}{QUERY_PARAMS}&p={page_num}" if page_num > 1 else f"{BASE_URL}{QUERY_PARAMS}"
    print(f"\n[PAGE] Fetching page {page_num}: {url}")

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        print(f"  [x] Failed to load page")
        await page.close()
        return False, []

    # Wait for job cards to appear
    try:
        await page.wait_for_selector("a[href*='/vacatures/']", timeout=30000)
    except Exception as e:
        print(f"  [!] No job cards found")
        await page.close()
        return False, []

    # Extract job URLs from this page
    # Use a more specific selector to avoid pagination links
    # Job detail URLs have pattern: /vacatures/{NUMERIC_ID}/...
    job_links = await page.query_selector_all("a[href*='/vacatures/'][href*='-']")
    page_job_urls = []

    for link in job_links:
        href = await link.get_attribute("href")
        if href and "/vacatures/" in href:
            # Filter to only numeric ID + title pattern (not pagination/filter links)
            if re.search(r'/vacatures/\d+/', href):
                full_url = href if href.startswith("http") else f"https://www.vdab.be{href}"
                page_job_urls.append(full_url)

    page_job_urls = list(set(page_job_urls))  # Remove duplicates
    print(f"  Found {len(page_job_urls)} job listings on this page")

    await page.close()

    # Stop pagination if this page has no jobs (we've hit the end)
    if len(page_job_urls) == 0:
        print(f"  [i] No jobs found on this page. Reached end of results.")
        return False, page_job_urls

    # Also stop if we hit a reasonable upper limit (safety valve)
    if page_num > 65:
        print(f"  [i] Reached page limit (65). Stopping pagination.")
        return False, page_job_urls

    return True, page_job_urls

async def scrape_jobs(browser, page_urls, processed_ids):
    """Scrape individual job detail pages."""
    new_processed = len(processed_ids)

    for job_url in page_urls:
        job_id = extract_job_id_from_url(job_url)
        if not job_id:
            print(f"  [!] Could not extract job ID")
            continue

        if job_id in processed_ids:
            print(f"  [--] Skipping {job_id}")
            continue

        print(f"  [>] Scraping {job_id}")

        try:
            details = await extract_job_details(browser, job_url)
            save_job_markdown(job_id, details)
            processed_ids.add(job_id)
            save_processed(processed_ids)
            new_processed += 1
            try:
                title_safe = details['title'][:40] if details['title'] != '[MISSING]' else '[MISSING]'
                print(f"  [+] {job_id}")
            except:
                print(f"  [+] {job_id}")

            # Rate limiting between jobs
            sleep_time = random.uniform(2, 5)
            await asyncio.sleep(sleep_time)
        except Exception as e:
            print(f"  [x] {job_id}")

    return new_processed

async def main():
    ensure_jobs_dir()
    processed_ids = load_processed()
    print(f"[*] Loaded {len(processed_ids)} already-processed job IDs\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        all_job_urls = []
        page_num = 1
        continue_pagination = True

        while continue_pagination:
            print(f"\n>>> PAGE {page_num}")
            continue_pagination, page_urls = await scrape_page(browser, page_num, processed_ids, all_job_urls)
            print(f">>> Got {len(page_urls)} URLs, continue={continue_pagination}")
            all_job_urls.extend(page_urls)

            if page_urls:
                new_processed = await scrape_jobs(browser, page_urls, processed_ids)

            if continue_pagination:
                sleep_time = random.uniform(3, 7)
                print(f"\n[*] Waiting {sleep_time:.1f}s before next page...")
                await asyncio.sleep(sleep_time)

            page_num += 1

        await browser.close()

    print(f"\n[+] Scraping complete!")
    print(f"[*] Total processed jobs: {len(processed_ids)}")
    print(f"[*] Jobs saved in: {JOBS_DIR.resolve()}")

if __name__ == "__main__":
    asyncio.run(main())
