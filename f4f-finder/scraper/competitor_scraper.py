from playwright.async_api import async_playwright
from .base_scraper import BaseScraper

class CompetitorScraper(BaseScraper):

    async def extract_companies(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(self.url)
            
            anchors = await page.query_selector_all('a')
            results = []
            for a in anchors:
                text = await a.inner_text()
                text = text.strip()
                href = await a.get_attribute('href')
                if href and 'retailer' in href.lower():
                    results.append({'name': text, 'domain': href.split('/')[2], 'source': 'competitor'})
            
            await browser.close()
            return results

