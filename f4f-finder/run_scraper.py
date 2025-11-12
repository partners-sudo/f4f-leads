from tasks import scrape_competitor_partners, scrape_linkedin_companies, scrape_marketplaces

if __name__ == '__main__':
    scrape_competitor_partners.delay('https://example.com/where-to-buy')
    scrape_linkedin_companies.delay('retail buyer')
    scrape_marketplaces.delay('https://shopify.com/shops')

