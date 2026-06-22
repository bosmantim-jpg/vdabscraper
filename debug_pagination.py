#!/usr/bin/env python3
import asyncio
import re
from playwright.async_api import async_playwright

async def test_pages():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for page_num in [1, 2, 3, 4, 5, 6, 7, 8]:
            page = await browser.new_page()

            base_url = "https://www.vdab.be/vindeenjob/vacatures"
            params = "?trefwoord=credit&arbeidscircuit=8&sort=standaard"
            url = f"{base_url}{params}&p={page_num}" if page_num > 1 else f"{base_url}{params}"

            print(f"\n[PAGE {page_num}] {url[:80]}...")

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except:
                    pass

                # Use the scraper's selector
                job_links = await page.query_selector_all("a[href*='/vacatures/'][href*='-']")
                job_urls = []

                for link in job_links:
                    href = await link.get_attribute("href")
                    if href and re.search(r'/vacatures/\d+/', href):
                        job_urls.append(href)

                print(f"  Found {len(job_urls)} jobs")

                if len(job_urls) == 0:
                    print(f"  >>> NO JOBS ON THIS PAGE - WOULD STOP HERE <<<")
                    break

                # Show first 2
                for i, url in enumerate(job_urls[:2], 1):
                    job_id = re.search(r'/vacatures/(\d+)/', url)
                    if job_id:
                        print(f"    Job {i}: {job_id.group(1)}")

            except Exception as e:
                print(f"  ERROR: {e}")
                break

            finally:
                await page.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_pages())
