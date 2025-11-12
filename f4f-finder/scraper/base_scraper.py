from playwright.sync_api import sync_playwright

class BaseScraper:

    def __init__(self, url):
        self.url = url

    def open_page(self, headless=True):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.page = self.browser.new_page()
        self.page.goto(self.url)

    def close(self):
        self.browser.close()
        self.playwright.stop()

