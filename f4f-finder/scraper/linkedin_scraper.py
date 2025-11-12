# scraper/linkedin_scraper.py
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from utils.logger import logger
import os
from dotenv import load_dotenv
import json
import re
from urllib.parse import urlparse
from pathlib import Path

load_dotenv()

# Path to store browser state (cookies/session)
STATE_FILE = Path(__file__).parent.parent / ".linkedin_state.json"
# Path to .env file
ENV_FILE = Path(__file__).parent.parent / ".env"

class LinkedInScraper(BaseScraper):
    def __init__(self, keyword):
        self.keyword = keyword
        # Fixed: use the keyword parameter instead of hardcoded "f4f"
        self.base_url = f"https://www.linkedin.com/search/results/companies/?keywords={keyword}"
        self.linkedin_email = os.environ.get("LINKEDIN_EMAIL")
        self.linkedin_password = os.environ.get("LINKEDIN_PASSWORD")
        super().__init__(self.base_url)
    
    def load_browser_state(self):
        """Load saved browser state (cookies/session) if it exists."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                    logger.info("Loaded saved LinkedIn browser state")
                    return state
            except Exception as e:
                logger.warning(f"Failed to load browser state: {e}")
        return None
    
    async def save_browser_state(self, context):
        """Save browser state (cookies/session) for future use."""
        try:
            # storage_state() is async in Playwright
            state = await context.storage_state()
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f)
            logger.info("Saved LinkedIn browser state for future use")
        except Exception as e:
            logger.error(f"Failed to save browser state: {e}")
    
    async def handle_verification_code(self, page):
        """Handle LinkedIn verification code input."""
        try:
            # Check if we're on a verification code page
            verification_selectors = [
                "input#input__email_verification_pin",
                "input[name='pin']",
                "input[type='text'][id*='verification']",
                "input[type='text'][id*='pin']",
                "input[type='text'][id*='code']"
            ]
            
            code_input = None
            for selector in verification_selectors:
                try:
                    code_input = await page.wait_for_selector(selector, timeout=5000)
                    if code_input:
                        logger.info(f"Found verification code input with selector: {selector}")
                        break
                except:
                    continue
            
            if not code_input:
                logger.warning("Could not find verification code input field")
                return False
            
            # Try to get verification code from environment variable first
            verification_code = os.environ.get("LINKEDIN_VERIFICATION_CODE")
            
            if verification_code:
                logger.info(f"Using verification code from environment variable: {verification_code[:2]}****")
                try:
                    # Clear and fill the code input (Playwright doesn't have .clear(), use fill with empty string first)
                    await code_input.fill('')
                    await page.wait_for_timeout(200)
                    await code_input.fill(verification_code.strip())
                    await page.wait_for_timeout(1000)
                    
                    # Verify the code was actually entered
                    entered_value = await code_input.input_value()
                    logger.info(f"Code entered in field: {entered_value[:2]}**** (length: {len(entered_value)})")
                    if entered_value != verification_code.strip():
                        logger.warning(f"Warning: Entered code doesn't match! Expected: {verification_code.strip()}, Got: {entered_value}")
                    
                    # Try to find and click submit button
                    submit_selectors = [
                        "button[type='submit']",
                        "button:has-text('Verify')",
                        "button:has-text('Submit')",
                        "input[type='submit']"
                    ]
                    submit_clicked = False
                    for selector in submit_selectors:
                        try:
                            submit_btn = await page.query_selector(selector)
                            if submit_btn:
                                await submit_btn.click()
                                logger.info("Clicked verification submit button")
                                submit_clicked = True
                                break
                        except:
                            continue
                    
                    if not submit_clicked:
                        logger.error("Could not find or click submit button")
                        return False
                    
                    # Wait for page to process and check result
                    await page.wait_for_timeout(5000)
                    current_url = page.url
                    logger.info(f"After verification submit, current URL: {current_url}")
                    
                    # Check for error messages - try multiple selectors
                    try:
                        error_selectors = [
                            "[class*='error']",
                            "[class*='alert']",
                            "[id*='error']",
                            ".alert-error",
                            ".error-message",
                            "[role='alert']",
                            ".challenge-error",
                            "div[class*='error']"
                        ]
                        error_found = False
                        for error_sel in error_selectors:
                            try:
                                error_elements = await page.query_selector_all(error_sel)
                                for error_el in error_elements:
                                    error_text = await error_el.inner_text()
                                    if error_text and len(error_text.strip()) > 0 and len(error_text.strip()) < 200:
                                        logger.warning(f"LinkedIn error message: {error_text.strip()}")
                                        error_found = True
                            except:
                                continue
                        
                        # Also check page text for common error messages
                        if not error_found:
                            page_text = await page.evaluate("() => document.body.innerText")
                            error_keywords = ["incorrect", "invalid", "expired", "wrong", "try again", "error"]
                            for keyword in error_keywords:
                                if keyword.lower() in page_text.lower():
                                    # Find the sentence containing the keyword
                                    sentences = page_text.split('.')
                                    for sentence in sentences:
                                        if keyword.lower() in sentence.lower():
                                            logger.warning(f"Possible error message found: {sentence.strip()[:100]}")
                                            break
                    except Exception as e:
                        logger.debug(f"Error checking for error messages: {e}")
                    
                    # Check if verification was successful
                    if "challenge" not in current_url.lower() and "verification" not in current_url.lower() and "checkpoint" not in current_url.lower():
                        logger.info("Verification successful!")
                        return True
                    else:
                        logger.warning(f"Still on verification/challenge page: {current_url}")
                        logger.warning("The verification code may be incorrect or expired. Please check your email for a new code.")
                        return False
                        
                except Exception as e:
                    logger.error(f"Error submitting verification code: {e}")
                    return False
            else:
                # If no code in env, log instructions
                logger.warning("=" * 80)
                logger.warning("LINKEDIN VERIFICATION CODE REQUIRED")
                logger.warning("=" * 80)
                logger.warning("LinkedIn sent a verification code to your email.")
                logger.warning("Add LINKEDIN_VERIFICATION_CODE=XXXXXX to .env file (no restart needed)")
                logger.warning("=" * 80)
                # Wait up to 5 minutes for code to be set in env
                logger.info("Waiting up to 5 minutes for verification code in env...")
                logger.info("You can add LINKEDIN_VERIFICATION_CODE to .env file - it will be picked up automatically")
                logger.info(f"Looking for .env file at: {ENV_FILE}")
                for i in range(60):  # 60 * 5 seconds = 5 minutes
                    await page.wait_for_timeout(5000)
                    # Reload .env file to pick up new verification code (specify exact path)
                    if ENV_FILE.exists():
                        load_dotenv(dotenv_path=ENV_FILE, override=True)
                    else:
                        # Fallback to default location
                        load_dotenv(override=True)
                    # Re-check env variable
                    new_code = os.environ.get("LINKEDIN_VERIFICATION_CODE")
                    if new_code and new_code.strip():
                        logger.info(f"Found verification code in environment: {new_code[:2]}**** (submitting...)")
                        try:
                            # Clear and fill the code input
                            await code_input.fill('')
                            await page.wait_for_timeout(200)
                            await code_input.fill(new_code.strip())
                            await page.wait_for_timeout(1000)
                            
                            # Try to find and click submit button
                            submit_btn = await page.query_selector("button[type='submit'], button:has-text('Verify'), button:has-text('Submit')")
                            if submit_btn:
                                logger.info("Clicking submit button...")
                                await submit_btn.click()
                                await page.wait_for_timeout(5000)
                                current_url = page.url
                                logger.info(f"After submit, current URL: {current_url}")
                                if "challenge" not in current_url.lower() and "verification" not in current_url.lower():
                                    logger.info("Verification successful!")
                                    return True
                                else:
                                    logger.warning("Still on verification page, may need to retry")
                            else:
                                logger.warning("Could not find submit button")
                        except Exception as e:
                            logger.error(f"Error submitting verification code: {e}")
                    else:
                        if i % 6 == 0:  # Log every 30 seconds
                            logger.debug(f"Still waiting for verification code... (checked {i+1} times)")
                    current_url = page.url
                    if "challenge" not in current_url.lower() and "login" not in current_url.lower():
                        logger.info("Verification appears to be complete!")
                        return True
                logger.error("Timeout waiting for verification code")
                return False
                
        except Exception as e:
            logger.error(f"Error handling verification code: {e}")
            return False
    
    async def login(self, page, context):
        """Login to LinkedIn if credentials are provided."""
        if not self.linkedin_email or not self.linkedin_password:
            logger.warning("LinkedIn credentials not found in environment variables. Skipping login.")
            return False
        
        try:
            logger.info("Attempting to login to LinkedIn...")
            await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            
            # Wait for and fill email field
            email_selectors = [
                "input#username",
                "input[name='session_key']",
                "input[type='text'][autocomplete='username']"
            ]
            email_filled = False
            for selector in email_selectors:
                try:
                    email_input = await page.wait_for_selector(selector, timeout=5000)
                    if email_input:
                        await email_input.fill(self.linkedin_email)
                        email_filled = True
                        logger.info("Email field filled")
                        break
                except:
                    continue
            
            if not email_filled:
                logger.error("Could not find email input field")
                return False
            
            # Wait for and fill password field
            password_selectors = [
                "input#password",
                "input[name='session_password']",
                "input[type='password']"
            ]
            password_filled = False
            for selector in password_selectors:
                try:
                    password_input = await page.wait_for_selector(selector, timeout=5000)
                    if password_input:
                        await password_input.fill(self.linkedin_password)
                        password_filled = True
                        logger.info("Password field filled")
                        break
                except:
                    continue
            
            if not password_filled:
                logger.error("Could not find password input field")
                return False
            
            # Click login button
            login_button_selectors = [
                "button[type='submit']",
                "button.btn-primary",
                "input[type='submit']"
            ]
            login_clicked = False
            for selector in login_button_selectors:
                try:
                    login_button = await page.query_selector(selector)
                    if login_button:
                        await login_button.click()
                        login_clicked = True
                        logger.info("Login button clicked")
                        break
                except:
                    continue
            
            if not login_clicked:
                logger.error("Could not find login button")
                return False
            
            # Wait for navigation after login
            await page.wait_for_timeout(5000)
            
            # Check if we need verification code
            current_url = page.url
            if "challenge" in current_url.lower() or "verification" in current_url.lower():
                logger.info("LinkedIn requires verification code...")
                verification_success = await self.handle_verification_code(page)
                if not verification_success:
                    return False
                # Re-check URL after verification
                await page.wait_for_timeout(3000)
                current_url = page.url
            
            # Check if login was successful
            if "login" not in current_url.lower() and "challenge" not in current_url.lower():
                logger.info(f"Login successful! Current URL: {current_url}")
                # Save browser state for future use
                await self.save_browser_state(context)
                return True
            else:
                logger.warning(f"Login may have failed. Still on: {current_url}")
                return False
                
        except Exception as e:
            logger.error(f"Error during LinkedIn login: {e}")
            return False

    def parse_country(self, text):
        """Parse country from headquarters text."""
        if not text:
            return None
        
        text_lower = text.lower()
        
        # Common country patterns
        country_patterns = {
            "US": ["united states", "usa", "u.s.a", "u.s.", "america"],
            "UK": ["united kingdom", "u.k.", "uk", "england", "scotland", "wales"],
            "CA": ["canada"],
            "AU": ["australia"],
            "DE": ["germany", "deutschland"],
            "FR": ["france"],
            "IT": ["italy", "italia"],
            "ES": ["spain", "españa"],
            "NL": ["netherlands", "holland"],
            "BE": ["belgium"],
            "CH": ["switzerland"],
            "AT": ["austria"],
            "SE": ["sweden"],
            "NO": ["norway"],
            "DK": ["denmark"],
            "FI": ["finland"],
            "PL": ["poland"],
            "IE": ["ireland"],
            "PT": ["portugal"],
            "GR": ["greece"],
            "CZ": ["czech republic", "czechia"],
            "HU": ["hungary"],
            "RO": ["romania"],
            "BG": ["bulgaria"],
        }
        
        for country_code, patterns in country_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    return country_code
        
        # If no match, try to extract last part (often country)
        parts = text.split(",")
        if len(parts) > 1:
            last_part = parts[-1].strip()
            # If it's a short string, might be country
            if len(last_part) <= 30:
                return last_part
        
        return None
    
    def parse_region(self, text):
        """Parse region from headquarters text."""
        if not text:
            return None
        
        # Extract region (usually city, state/province, country)
        # Return the full location string as region
        parts = text.split(",")
        if len(parts) >= 2:
            # Return everything except the last part (country) as region
            region = ",".join(parts[:-1]).strip()
            return region if region else None
        
        return text.strip() if text.strip() else None

    async def extract_company_details(self, page, company_url):
        """Extract detailed company information from a LinkedIn company /about/ page."""
        company_data = {}
        
        try:
            # Ensure we visit the /about/ page specifically
            if not company_url.endswith("/about/"):
                # Remove trailing slash if present, then add /about/
                company_url = company_url.rstrip("/") + "/about/"
            
            logger.info(f"Visiting company /about/ page: {company_url}")
            await page.goto(company_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Wait for the about page content to load
            try:
                # Wait for common about page elements
                await page.wait_for_selector(
                    "h1, div.org-about-us-organization-description, section[data-test-id='about-section'], dt, dd",
                    timeout=10000
                )
            except Exception as e:
                logger.debug(f"Timeout waiting for about page elements: {e}")
            
            # Check if we're blocked or redirected
            current_url = page.url
            logger.info(f"Current URL after navigation: {current_url}")
            
            # Verify we're on the /about/ page
            if "/about/" not in current_url:
                logger.warning(f"Not on /about/ page! Current URL: {current_url}, expected: {company_url}")
                # Try to navigate to /about/ again
                if "/company/" in current_url:
                    about_url = current_url.rstrip("/") + "/about/"
                    logger.info(f"Attempting to navigate to /about/ page: {about_url}")
                    await page.goto(about_url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)
                    current_url = page.url
                    logger.info(f"URL after retry: {current_url}")
            
            if "login" in current_url.lower() or "authwall" in current_url.lower():
                logger.warning(f"Redirected to login/authwall when accessing {company_url}")
                return company_data
            
            # Extract company name from page header (h1)
            name_selectors = [
                "h1.org-top-card-summary__title",
                "h1.text-heading-xlarge",
                "h1[data-test-id='org-name']",
                "h1.org-top-card-summary-info__primary-content",
                "h1"
            ]
            for selector in name_selectors:
                try:
                    name_el = await page.query_selector(selector)
                    if name_el:
                        company_name = (await name_el.inner_text()).strip()
                        if company_name:
                            company_data["name"] = company_name
                            break
                except:
                    continue
            
            # Extract company website/domain from About section
            # The website is usually in a link in the About section
            website_selectors = [
                "a[href^='http']:not([href*='linkedin.com']):not([href*='facebook.com']):not([href*='twitter.com'])",
                "a.org-about-us-organization-description__website",
                "a[data-test-id='org-website']",
                "div.org-about-us-organization-description a[href^='http']",
                "section[data-test-id='about-section'] a[href^='http']"
            ]
            for selector in website_selectors:
                try:
                    website_els = await page.query_selector_all(selector)
                    for website_el in website_els:
                        website = await website_el.get_attribute("href")
                        if website and not any(domain in website.lower() for domain in ["linkedin.com", "facebook.com", "twitter.com", "instagram.com"]):
                            # Clean up the URL and extract domain
                            website = website.strip()
                            if website.startswith("//"):
                                website = "https:" + website
                            elif not website.startswith("http"):
                                website = "https://" + website
                            
                            # Extract domain from URL
                            try:
                                parsed = urlparse(website)
                                domain = parsed.netloc or parsed.path
                                # Remove www. prefix
                                if domain.startswith("www."):
                                    domain = domain[4:]
                                company_data["domain"] = domain
                                company_data["website"] = website  # Keep full URL for reference
                                break
                            except:
                                company_data["domain"] = website
                                company_data["website"] = website
                                break
                    if company_data.get("domain"):
                        break
                except:
                    continue
            
            # Extract headquarters information (for country and region)
            headquarters_text = None
            
            # Try multiple strategies to find headquarters
            try:
                # Strategy 1: Look for definition list (dt/dd) pattern
                dt_elements = await page.query_selector_all("dt")
                for dt_el in dt_elements:
                    try:
                        dt_text = (await dt_el.inner_text()).strip().lower()
                        if "headquarters" in dt_text:
                            # Get the next dd element (sibling)
                            dd_el = await dt_el.evaluate_handle("el => el.nextElementSibling")
                            if dd_el and dd_el.as_element():
                                headquarters_text = (await dd_el.as_element().inner_text()).strip()
                                if headquarters_text:
                                    break
                    except:
                        continue
                
                # Strategy 2: Look for data-test-id attribute
                if not headquarters_text:
                    hq_el = await page.query_selector("div[data-test-id='org-headquarters'], span[data-test-id='org-headquarters']")
                    if hq_el:
                        headquarters_text = (await hq_el.inner_text()).strip()
                
                # Strategy 3: Search by text content pattern
                if not headquarters_text:
                    page_text = await page.evaluate("() => document.body.innerText")
                    if "Headquarters" in page_text:
                        # Use JavaScript to find the element containing headquarters
                        hq_text = await page.evaluate("""
                            () => {
                                const allElements = document.querySelectorAll('dt, dd, div, span, p, li');
                                for (let el of allElements) {
                                    const text = el.textContent || el.innerText || '';
                                    if (text.toLowerCase().includes('headquarters')) {
                                        // Try to get the value part (usually after "Headquarters")
                                        const parts = text.split(/headquarters/i);
                                        if (parts.length > 1) {
                                            const value = parts[1].trim().split(/[\\n\\r]/)[0].trim();
                                            if (value && value.length > 3 && value.length < 200) {
                                                return value;
                                            }
                                        }
                                        // Or get the next sibling
                                        const nextSibling = el.nextElementSibling;
                                        if (nextSibling) {
                                            const siblingText = (nextSibling.textContent || nextSibling.innerText || '').trim();
                                            if (siblingText && siblingText.length > 3 && siblingText.length < 200) {
                                                return siblingText;
                                            }
                                        }
                                    }
                                }
                                return null;
                            }
                        """)
                        if hq_text:
                            headquarters_text = hq_text
            except Exception as e:
                logger.debug(f"Error finding headquarters: {e}")
            
            # Parse country and region from headquarters
            if headquarters_text:
                company_data["country"] = self.parse_country(headquarters_text)
                company_data["region"] = self.parse_region(headquarters_text)
                company_data["headquarters"] = headquarters_text  # Keep full text for reference
            
            # Extract company type (usually "Company size" or "Type" field)
            # This maps to the "type" field in the schema
            type_selectors = [
                "dt:has-text('Company size') + dd",
                "dt:has-text('Type') + dd",
                "div[data-test-id='org-type']",
            ]
            for selector in type_selectors:
                try:
                    type_el = await page.query_selector(selector)
                    if type_el:
                        company_type = (await type_el.inner_text()).strip()
                        if company_type:
                            company_data["type"] = company_type
                            break
                except:
                    continue
            
            # If no type found, default to "brand" as suggested
            if not company_data.get("type"):
                company_data["type"] = "brand"
            
            # Set source
            company_data["source"] = "linkedin"
            
            # Set brand_focus from keyword (will be set in the calling function)
            # This will be added when creating the company record
            
            # Extract LinkedIn URL (base URL without /about/)
            base_url = company_url.replace("/about/", "").rstrip("/")
            company_data["linkedin_url"] = base_url
            
            logger.debug(f"Extracted details for company: {company_data.get('name', 'Unknown')} - Domain: {company_data.get('domain', 'N/A')}, Country: {company_data.get('country', 'N/A')}")
            
        except Exception as e:
            logger.error(f"Error extracting company details from {company_url}: {e}")
        
        return company_data

    async def extract_contacts(self):
        async with async_playwright() as p:
            # Use a more realistic browser context to avoid detection
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            # Try to load saved browser state (cookies/session)
            saved_state = self.load_browser_state()
            context_options = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            if saved_state:
                context_options['storage_state'] = saved_state
                logger.info("Using saved browser state - should be logged in already")
            
            context = await browser.new_context(**context_options)
            page = await context.new_page()
            
            logger.info(f"Navigating to LinkedIn search: {self.base_url}")
            await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait a bit for JavaScript to execute
            await page.wait_for_timeout(3000)
            
            # Check if we're on a login page
            current_url = page.url
            logger.info(f"Current page URL: {current_url}")
            if "login" in current_url.lower() or "authwall" in current_url.lower():
                logger.info("LinkedIn redirected to login page - attempting to login...")
                login_success = await self.login(page, context)
                if not login_success:
                    logger.error("Failed to login to LinkedIn. Cannot proceed with scraping.")
                    await browser.close()
                    return []
                
                # After successful login, navigate to the search page again
                logger.info("Navigating to search page after login...")
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)
                
                # Verify we're not on login page anymore
                current_url = page.url
                if "login" in current_url.lower() or "authwall" in current_url.lower():
                    logger.error("Still on login page after login attempt. Cannot proceed.")
                    await browser.close()
                    return []
            
            # Wait for search results container to appear
            logger.info("Waiting for LinkedIn search results to load...")
            try:
                # Wait for the search results container - LinkedIn uses various containers
                await page.wait_for_selector(
                    "div.search-results-container, ul.reusable-search__entity-result-list, div.entity-result, li.reusable-search__result-container",
                    timeout=15000
                )
                logger.info("Search results container found")
            except Exception as e:
                logger.warning(f"Timeout waiting for search results container: {e}")
            
            # Additional wait for dynamic content
            await page.wait_for_timeout(2000)
            
            # Try scrolling to trigger lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await page.wait_for_timeout(1000)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(1000)
            
            results = []

            # Find all company links directly from the page
            # LinkedIn company search results contain links with "/company/" in the href
            logger.info("Searching for company links in search results...")
            
            # Strategy 1: Find all links that contain "/company/" in their href
            all_links = await page.query_selector_all("a[href*='/company/']")
            logger.info(f"Found {len(all_links)} links containing '/company/'")
            
            # Extract unique company URLs
            company_urls = []
            seen_urls = set()
            
            for link in all_links:
                try:
                    href = await link.get_attribute("href")
                    if not href:
                        continue
                    
                    # Clean up the URL
                    if not href.startswith("http"):
                        href = f"https://www.linkedin.com{href}"
                    
                    # Extract the base company URL (remove query params, fragments, etc.)
                    # e.g., "https://www.linkedin.com/company/xyz-ltd/?originalSubdomain=uk" -> "https://www.linkedin.com/company/xyz-ltd"
                    if "/company/" in href:
                        # Get the base URL up to the company slug
                        parts = href.split("/company/")
                        if len(parts) > 1:
                            company_slug = parts[1].split("?")[0].split("#")[0].rstrip("/")
                            base_url = f"https://www.linkedin.com/company/{company_slug}"
                            
                            if base_url not in seen_urls:
                                seen_urls.add(base_url)
                                
                                # Try to get company name from the link or nearby elements
                                company_name = None
                                try:
                                    # Try to get text from the link itself
                                    link_text = await link.inner_text()
                                    if link_text and link_text.strip():
                                        company_name = link_text.strip()
                                    
                                    # If no text in link, try to find name in parent/sibling elements
                                    if not company_name:
                                        parent = await link.evaluate_handle("el => el.closest('li, div[class*=\"result\"], div[class*=\"entity\"]')")
                                        if parent and parent.as_element():
                                            parent_text = await parent.as_element().inner_text()
                                            # Extract first meaningful line (usually company name)
                                            lines = [l.strip() for l in parent_text.split("\n") if l.strip()]
                                            if lines:
                                                company_name = lines[0]
                                except Exception as e:
                                    logger.debug(f"Error extracting company name: {e}")
                                
                                # Get region/location if available
                                region = None
                                try:
                                    # Look for location in the same card
                                    card = await link.evaluate_handle("el => el.closest('li, div[class*=\"result\"], div[class*=\"entity\"]')")
                                    if card and card.as_element():
                                        card_text = await card.as_element().inner_text()
                                        # Look for common location patterns
                                        lines = [l.strip() for l in card_text.split("\n") if l.strip()]
                                        for line in lines[1:]:  # Skip first line (company name)
                                            # Location usually contains commas or common location keywords
                                            if "," in line or any(keyword in line.lower() for keyword in ["followers", "employees", "location"]):
                                                # Skip if it's a number or follower count
                                                if not re.match(r'^\d+', line) and "follower" not in line.lower():
                                                    region = line
                                                    break
                                except Exception as e:
                                    logger.debug(f"Error extracting region: {e}")
                                
                                if company_name:
                                    company_urls.append({
                                        "company_name": company_name,
                                        "linkedin_url": base_url,
                                        "region": region
                                    })
                                    logger.debug(f"Found company: {company_name} - {base_url}")
                except Exception as e:
                    logger.debug(f"Error processing company link: {e}")
                    continue
            
            # If we didn't find companies via links, try the card-based approach as fallback
            if not company_urls:
                logger.info("Trying fallback: card-based extraction...")
                selectors_to_try = [
                    "li.reusable-search__result-container",
                    "div.entity-result",
                    "div.entity-result__content",
                    "div.search-result__wrapper",
                ]
                
                company_cards = []
                for selector in selectors_to_try:
                    company_cards = await page.query_selector_all(selector)
                    if company_cards:
                        logger.info(f"Found {len(company_cards)} company cards using selector: {selector}")
                        break
                
                for card in company_cards:
                    try:
                        # Find all links in the card
                        card_links = await card.query_selector_all("a[href*='/company/']")
                        for link in card_links:
                            href = await link.get_attribute("href")
                            if href and "/company/" in href:
                                if not href.startswith("http"):
                                    href = f"https://www.linkedin.com{href}"
                                
                                # Extract base URL
                                parts = href.split("/company/")
                                if len(parts) > 1:
                                    company_slug = parts[1].split("?")[0].split("#")[0].rstrip("/")
                                    base_url = f"https://www.linkedin.com/company/{company_slug}"
                                    
                                    if base_url not in seen_urls:
                                        seen_urls.add(base_url)
                                        
                                        # Get company name
                                        company_name = None
                                        name_selectors = [
                                            "span.entity-result__title-text",
                                            "a.app-aware-link span",
                                            "div.entity-result__title-text a span",
                                            "h3.search-result__title a span",
                                        ]
                                        for name_sel in name_selectors:
                                            name_el = await card.query_selector(name_sel)
                                            if name_el:
                                                company_name = (await name_el.inner_text()).strip()
                                                if company_name:
                                                    break
                                        
                                        # Get region
                                        region = None
                                        location_el = await card.query_selector(
                                            "div.entity-result__primary-subtitle, "
                                            "div.search-result__snippets, "
                                            "span.entity-result__secondary-subtitle"
                                        )
                                        if location_el:
                                            region = (await location_el.inner_text()).strip()
                                        
                                        if company_name:
                                            company_urls.append({
                                                "company_name": company_name,
                                                "linkedin_url": base_url,
                                                "region": region
                                            })
                                            logger.debug(f"Found company (fallback): {company_name} - {base_url}")
                    except Exception as e:
                        logger.debug(f"Error extracting from card: {e}")
                        continue

            logger.info(f"Found {len(company_urls)} companies. Now extracting detailed information...")
            
            # Now visit each company profile page to get detailed information
            for idx, company_info in enumerate(company_urls, 1):
                try:
                    logger.info(f"Processing company {idx}/{len(company_urls)}: {company_info['company_name']}")
                    
                    # Extract detailed company information from /about/ page
                    detailed_data = await self.extract_company_details(page, company_info['linkedin_url'])
                    
                    # Build company record with proper field mapping
                    company_record = {
                        "name": detailed_data.get("name") or company_info.get("company_name"),
                        "source": detailed_data.get("source", "linkedin"),
                        "brand_focus": self.keyword  # Set brand_focus from search keyword
                    }
                    
                    # Add domain (extracted from website in extract_company_details)
                    if detailed_data.get("domain"):
                        company_record["domain"] = detailed_data["domain"]
                    else:
                        # Fallback: try to extract from LinkedIn URL or use placeholder
                        linkedin_url = company_info.get("linkedin_url") or detailed_data.get("linkedin_url")
                        if linkedin_url and "company" in linkedin_url:
                            # Try to extract company slug from LinkedIn URL as fallback
                            try:
                                parts = linkedin_url.split("/")
                                company_slug = [p for p in parts if p and p != "company"][-1] if "company" in parts else None
                                if company_slug:
                                    company_record["domain"] = f"{company_slug}.linkedin.com"
                                else:
                                    company_record["domain"] = None  # Will be enriched later
                            except:
                                company_record["domain"] = None
                        else:
                            company_record["domain"] = None
                    
                    # Add country (parsed from headquarters)
                    if detailed_data.get("country"):
                        company_record["country"] = detailed_data["country"]
                    
                    # Add region (parsed from headquarters, or fallback to search result region)
                    if detailed_data.get("region"):
                        company_record["region"] = detailed_data["region"]
                    elif company_info.get("region"):
                        company_record["region"] = company_info.get("region")
                    
                    # Add type (from detailed data, defaults to "brand" if not found)
                    if detailed_data.get("type"):
                        company_record["type"] = detailed_data["type"]
                    else:
                        company_record["type"] = "brand"
                    
                    # Create contact record (will be linked to company via company_id in task)
                    contact_record = {
                        "linkedin_url": company_info.get("linkedin_url") or detailed_data.get("linkedin_url"),
                        "name": None,
                        "position": None,
                        "email": None
                    }
                    
                    # Store both company and contact data together
                    results.append({
                        "company": company_record,
                        "contact": contact_record,
                        # Keep additional metadata for logging
                        "_metadata": {
                            "headquarters": detailed_data.get("headquarters"),
                            "website": detailed_data.get("website"),
                            "linkedin_url": detailed_data.get("linkedin_url")
                        }
                    })
                    logger.info(f"✓ Extracted: {company_record['name']} - Domain: {company_record.get('domain', 'N/A')}, Country: {company_record.get('country', 'N/A')}, Region: {company_record.get('region', 'N/A')}, Type: {company_record.get('type', 'N/A')}")
                    
                    # Add a small delay between requests to avoid rate limiting
                    await page.wait_for_timeout(2000)
                    
                except Exception as e:
                    logger.error(f"Error processing company {company_info.get('company_name', 'Unknown')}: {e}")
                    # Still add basic info even if detailed extraction fails
                    company_record = {
                        "name": company_info.get("company_name"),
                        "domain": None,  # Will be enriched later
                        "region": company_info.get("region"),
                        "source": "linkedin",
                        "type": "brand",
                        "brand_focus": self.keyword
                    }
                    contact_record = {
                        "linkedin_url": company_info.get("linkedin_url"),
                        "name": None,
                        "position": None,
                        "email": None
                    }
                    results.append({
                        "company": company_record,
                        "contact": contact_record,
                        "_metadata": {}
                    })

            logger.info(f"Extracted {len(results)} companies with detailed information from LinkedIn search for '{self.keyword}'")
            await browser.close()
            return results