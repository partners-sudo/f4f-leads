from .base_scraper import BaseScraper

class CompetitorScraper(BaseScraper):

    def extract_companies(self):
        self.open_page()
        anchors = self.page.query_selector_all('a')
        results = []
        for a in anchors:
            text = a.inner_text().strip()
            href = a.get_attribute('href')
            if href and 'retailer' in href.lower():
                results.append({'name': text, 'domain': href.split('/')[2], 'source': 'competitor'})
        self.close()
        return results

