from celery_app import app

from supabase_client import sb

from scraper.competitor_scraper import CompetitorScraper

from scraper.linkedin_scraper import LinkedInScraper

from scraper.marketplace_scraper import MarketplaceScraper

from enrichment.email_verification import verify_email

from enrichment.clearbit_integration import enrich_company

@app.task(bind=True, max_retries=3)
def scrape_competitor_partners(self, url, source="competitor"):
    try:
        scraper = CompetitorScraper(url)
        companies = scraper.extract_companies()
        for c in companies:
            c['email'] = verify_email(c.get('email'))
            enriched = enrich_company(c.get('domain'))
            c.update(enriched)
            sb.table('companies').upsert(c).execute()
        return {'count': len(companies)}
    except Exception as e:
        raise self.retry(exc=e, countdown=60)

@app.task(bind=True)
def scrape_linkedin_companies(self, keyword):
    try:
        scraper = LinkedInScraper(keyword)
        contacts = scraper.extract_contacts()
        for contact in contacts:
            sb.table('contacts').upsert(contact).execute()
        return {'count': len(contacts)}
    except Exception as e:
        raise self.retry(exc=e, countdown=60)

@app.task(bind=True)
def scrape_marketplaces(self, marketplace_url):
    try:
        scraper = MarketplaceScraper(marketplace_url)
        companies = scraper.extract_listings()
        for c in companies:
            sb.table('companies').upsert(c).execute()
        return {'count': len(companies)}
    except Exception as e:
        raise self.retry(exc=e, countdown=60)
