# scraper/linkedin_scraper.py
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from utils.logger import logger
import os
from dotenv import load_dotenv
import json
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
            # storage_state() returns a dict synchronously
            state = context.storage_state()
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

            # Try multiple selector strategies for LinkedIn search results
            # LinkedIn's structure can vary, so we try different selectors
            selectors_to_try = [
                "li.reusable-search__result-container",  # Most common LinkedIn search result container
                "div.entity-result",  # Alternative container
                "div.entity-result__content",  # Content wrapper
                "div.search-result__wrapper",  # Another alternative
            ]
            
            company_cards = []
            for selector in selectors_to_try:
                company_cards = await page.query_selector_all(selector)
                if company_cards:
                    logger.info(f"Found {len(company_cards)} company cards using selector: {selector}")
                    break
            
            if not company_cards:
                logger.warning("No company cards found. Debugging page content...")
                # Log page title and some content for debugging
                page_title = await page.title()
                logger.info(f"Page title: {page_title}")
                
                # Check what's actually on the page
                page_content = await page.content()
                logger.debug(f"Page HTML length: {len(page_content)}")
                
                # Try to find any result-like elements
                all_divs = await page.query_selector_all("div")
                logger.info(f"Total divs on page: {len(all_divs)}")
                
                # Look for text that might indicate results
                body_text = await page.evaluate("() => document.body.innerText")
                logger.info(f"Page body text preview (first 1000 chars):\n{body_text[:1000]}")
                
                # Check for common LinkedIn classes
                search_result_indicators = [
                    "entity-result",
                    "search-result",
                    "reusable-search",
                    "results-list"
                ]
                for indicator in search_result_indicators:
                    elements = await page.query_selector_all(f"[class*='{indicator}']")
                    if elements:
                        logger.info(f"Found {len(elements)} elements with class containing '{indicator}'")
            
            for card in company_cards:
                try:
                    # Try multiple selectors for company name
                    company_name = None
                    name_selectors = [
                        "span.entity-result__title-text",
                        "a.app-aware-link span",
                        "div.entity-result__title-text a span",
                        "h3.search-result__title a span",
                    ]
                    for name_sel in name_selectors:
                        company_name_el = await card.query_selector(name_sel)
                        if company_name_el:
                            company_name = (await company_name_el.inner_text()).strip()
                            if company_name:
                                break
                    
                    # Get company link
                    domain_el = await card.query_selector("a.app-aware-link, a.entity-result__title-link")
                    domain_url = None
                    if domain_el:
                        domain_url = await domain_el.get_attribute("href")
                        if domain_url and not domain_url.startswith("http"):
                            domain_url = f"https://www.linkedin.com{domain_url}"
                    
                    # Get location/region
                    location_el = await card.query_selector(
                        "div.entity-result__primary-subtitle, "
                        "div.search-result__snippets, "
                        "span.entity-result__secondary-subtitle"
                    )
                    region = None
                    if location_el:
                        region = (await location_el.inner_text()).strip()

                    # Extract employees (simplified placeholder)
                    employee_name = None
                    title = None
                    linkedin_url = domain_url  # Use the company link as LinkedIn URL

                    if company_name:  # Only add if we found at least a company name
                        results.append({
                            "company_name": company_name,
                            "domain": domain_url,
                            "region": region,
                            "contact_name": employee_name,
                            "title": title,
                            "linkedin_url": linkedin_url,
                            "source": "linkedin"
                        })
                        logger.debug(f"Extracted company: {company_name} (region: {region})")
                except Exception as e:
                    logger.error(f"Error extracting LinkedIn card: {e}")

            logger.info(f"Extracted {len(results)} contacts from LinkedIn search for '{self.keyword}'")
            await browser.close()
            return results