import asyncio
from celery_app import app

from supabase_client import sb

from scraper.competitor_scraper import CompetitorScraper

from scraper.linkedin_scraper import LinkedInScraper

from scraper.marketplace_scraper import MarketplaceScraper

from enrichment.email_verification import verify_email

from enrichment.clearbit_integration import enrich_company


def run_async(coro):
    """Helper function to run async code in Celery tasks, handling event loop creation."""
    try:
        # Try to get the existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
        # If loop exists and is not closed, use it
        return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop exists in this thread (common during Celery retries)
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            asyncio.set_event_loop(None)


@app.task(bind=True, max_retries=3)
def scrape_competitor_partners(self, url, source="competitor"):
    try:
        scraper = CompetitorScraper(url)
        companies = run_async(scraper.extract_companies())
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
        contacts = run_async(scraper.extract_contacts())
        for contact in contacts:
            sb.table('contacts').upsert(contact).execute()
        return {'count': len(contacts)}
    except Exception as e:
        raise self.retry(exc=e, countdown=60)

@app.task(bind=True)
def scrape_marketplaces(self, marketplace_url):
    try:
        scraper = MarketplaceScraper(marketplace_url)
        companies = run_async(scraper.extract_listings())
        for c in companies:
            sb.table('companies').upsert(c).execute()
        return {'count': len(companies)}
    except Exception as e:
        raise self.retry(exc=e, countdown=60)
