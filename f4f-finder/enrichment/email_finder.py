"""
Email finder module for discovering email addresses from domains.
Uses multiple strategies including common patterns and web scraping.
"""
import re
from typing import List, Optional, Tuple
import httpx
from bs4 import BeautifulSoup
from utils.logger import logger
from enrichment.email_verification import verify_email, check_email_server_reachable


# Common email patterns to try
COMMON_EMAIL_PATTERNS = [
    'info',
    'contact',
    'hello',
    'support',
    'sales',
    'admin',
    'office',
    'general',
    'inquiries',
    'enquiry',
    'mail',
    'email',
    'team',
    'help',
    'service',
    'customerservice',
    'customer',
    'business',
    'marketing',
    'press',
    'media',
    'partnerships',
    'partners',
    'careers',
    'jobs',
    'hr',
    'legal',
    'privacy',
    'abuse',
    'postmaster',
    'webmaster',
    'hostmaster',
    'noc',
    'security',
    'billing',
    'accounts',
    'finance',
    'accounting',
    'orders',
    'order',
    'shop',
    'store',
    'retail',
    'wholesale',
    'buy',
    'purchase',
    'procurement',
    'vendor',
    'supplier',
]

# Spammy email patterns to filter out
SPAMMY_EMAIL_PATTERNS = [
    r'noreply',
    r'no-reply',
    r'no_reply',
    r'donotreply',
    r'do-not-reply',
    r'do_not_reply',
    r'automated',
    r'auto',
    r'notification',
    r'notifications',
    r'alert',
    r'alerts',
    r'system',
    r'systems',
    r'bot',
    r'bots',
    r'daemon',
    r'mailer-daemon',
    r'postmaster',
    r'webmaster',
    r'hostmaster',
    r'abuse',
    r'security',
    r'privacy',
    r'legal',
    r'copyright',
    r'cease',
    r'example\.com',
    r'test\.com',
    r'localhost',
    r'127\.0\.0\.1',
]


def extract_emails_from_text(text: str) -> List[str]:
    """
    Extract email addresses from text using regex.
    
    Args:
        text: Text to search for emails
        
    Returns:
        List of found email addresses
    """
    if not text:
        return []
    
    # Email regex pattern
    email_pattern = re.compile(
        r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
    )
    
    emails = email_pattern.findall(text.lower())
    # Remove duplicates while preserving order
    seen = set()
    unique_emails = []
    for email in emails:
        if email not in seen:
            seen.add(email)
            unique_emails.append(email)
    
    return unique_emails


def is_spammy_email(email: str) -> bool:
    """
    Check if an email address looks spammy or automated.
    
    Args:
        email: Email address to check
        
    Returns:
        True if email looks spammy, False otherwise
    """
    email_lower = email.lower()
    
    # Check against spammy patterns
    for pattern in SPAMMY_EMAIL_PATTERNS:
        if re.search(pattern, email_lower):
            return True
    
    return False


def filter_spammy_emails(emails: List[str]) -> List[str]:
    """
    Filter out spammy/automated email addresses.
    
    Args:
        emails: List of email addresses
        
    Returns:
        Filtered list of email addresses
    """
    filtered = []
    for email in emails:
        if not is_spammy_email(email):
            filtered.append(email)
        else:
            logger.debug(f"   Filtered out spammy email: {email}")
    
    return filtered


def find_emails_on_website(domain: str) -> List[str]:
    """
    Scrape website to find email addresses from specific pages.
    Visits: /, /contact, /about, /impressum
    
    Args:
        domain: Domain name
        
    Returns:
        List of found email addresses (filtered for spammy emails)
    """
    emails = []
    
    if not domain:
        return emails
    
    # Pages to check (as specified)
    pages_to_check = [
        f"https://{domain}",
        f"https://{domain}/contact",
        f"https://{domain}/about",
        f"https://{domain}/impressum",
    ]
    
    for url in pages_to_check:
        try:
            logger.info(f"   Scraping {url} for emails...")
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                response = client.get(url)
                if response.status_code == 200:
                    # Extract emails from HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # Get all text
                    text = soup.get_text()
                    # Also check mailto links
                    mailto_links = soup.find_all('a', href=re.compile(r'^mailto:', re.I))
                    for link in mailto_links:
                        email = link.get('href', '').replace('mailto:', '').strip()
                        # Remove query parameters if any
                        email = email.split('?')[0].split('&')[0]
                        if email:
                            emails.append(email.lower())
                    
                    # Extract from text
                    found_emails = extract_emails_from_text(text)
                    emails.extend(found_emails)
                    
                    logger.debug(f"   Found {len(found_emails)} emails on {url}")
                else:
                    logger.debug(f"   HTTP {response.status_code} for {url}")
        except httpx.TimeoutException:
            logger.debug(f"   Timeout scraping {url}")
            continue
        except Exception as e:
            logger.debug(f"   Could not scrape {url}: {e}")
            continue
    
    # Remove duplicates
    unique_emails = list(set(emails))
    
    # Filter out spammy emails
    filtered_emails = filter_spammy_emails(unique_emails)
    
    logger.info(f"   Found {len(filtered_emails)} valid emails after filtering (from {len(unique_emails)} total)")
    
    return filtered_emails


def generate_email_candidates(domain: str, company_name: Optional[str] = None) -> List[str]:
    """
    Generate potential email addresses using common patterns.
    Prioritizes: info@, sales@, contact@ (fallback guesses).
    
    Args:
        domain: Domain name
        company_name: Optional company name for more specific patterns
        
    Returns:
        List of potential email addresses
    """
    if not domain:
        return []
    
    candidates = []
    
    # Priority fallback guesses (as specified)
    priority_patterns = ['info', 'sales', 'contact']
    for pattern in priority_patterns:
        candidates.append(f"{pattern}@{domain}")
    
    # Add other common patterns
    for pattern in COMMON_EMAIL_PATTERNS:
        if pattern not in priority_patterns:
            candidates.append(f"{pattern}@{domain}")
    
    # If company name provided, try variations
    if company_name:
        # Clean company name
        name_clean = re.sub(r'[^a-z0-9]', '', company_name.lower())
        if name_clean:
            # First few characters
            if len(name_clean) > 3:
                candidates.append(f"{name_clean[:4]}@{domain}")
                candidates.append(f"{name_clean[:6]}@{domain}")
            # Full name
            candidates.append(f"{name_clean}@{domain}")
    
    return candidates


def find_emails(domain: str, company_name: Optional[str] = None, verify: bool = True, 
                check_smtp: bool = False) -> List[Tuple[str, float]]:
    """
    Find email addresses for a domain using multiple strategies.
    
    Args:
        domain: Domain name
        company_name: Optional company name
        verify: Whether to verify emails (default: True)
        check_smtp: Whether to check email server with SMTP (default: False)
        
    Returns:
        List of tuples (email, confidence_score) sorted by score descending
    """
    if not domain:
        logger.warning("No domain provided for email finding")
        return []
    
    logger.info(f"\n📧 Finding emails for domain: {domain}")
    
    email_scores = []  # List of (email, score) tuples
    seen_emails = set()  # Track emails we've already processed
    
    # Strategy 1: Scrape website for emails (/, /contact, /about, /impressum)
    logger.info("   Strategy 1: Scraping website pages...")
    scraped_emails = find_emails_on_website(domain)
    logger.info(f"   Found {len(scraped_emails)} emails via scraping")
    
    # Verify scraped emails
    for email in scraped_emails:
        if email not in seen_emails:
            seen_emails.add(email)
            if verify:
                verified_email, score = verify_email(email)
                if verified_email and score > 0.3:
                    # Optionally check SMTP if requested
                    if check_smtp:
                        email_domain = email.split('@')[1] if '@' in email else domain
                        has_mx, smtp_reachable = check_email_server_reachable(email_domain)
                        if smtp_reachable:
                            score = min(score + 0.1, 1.0)  # Boost score if SMTP reachable
                            logger.debug(f"   SMTP check passed for {email}, boosted score")
                    
                    email_scores.append((verified_email, score))
                    logger.info(f"   ✓ Verified scraped: {verified_email} (score: {score:.2f})")
            else:
                email_scores.append((email, 0.7))  # Higher default score for scraped emails
                logger.info(f"   ✓ Found scraped: {email}")
    
    # Strategy 2: Generate fallback guesses if no emails found
    if not email_scores:
        logger.info("   Strategy 2: No emails found, generating fallback guesses...")
        fallback_emails = ['info@', 'sales@', 'contact@']
        candidates = [f"{prefix}{domain}" for prefix in fallback_emails]
        
        for candidate in candidates:
            if candidate not in seen_emails:
                seen_emails.add(candidate)
                if verify:
                    verified_email, score = verify_email(candidate)
                    if verified_email and score > 0.3:
                        # Optionally check SMTP if requested
                        if check_smtp:
                            has_mx, smtp_reachable = check_email_server_reachable(domain)
                            if smtp_reachable:
                                score = min(score + 0.1, 1.0)
                                logger.debug(f"   SMTP check passed for {verified_email}, boosted score")
                        
                        email_scores.append((verified_email, score))
                        logger.info(f"   ✓ Verified fallback: {verified_email} (score: {score:.2f})")
                else:
                    email_scores.append((candidate, 0.5))  # Lower default score for fallback guesses
                    logger.info(f"   ✓ Generated fallback: {candidate}")
    else:
        # Strategy 3: Generate additional candidates if we found some emails
        logger.info("   Strategy 3: Generating additional email candidates...")
        candidates = generate_email_candidates(domain, company_name)
        logger.debug(f"   Generated {len(candidates)} email candidates")
        
        # Verify candidates if requested
        if verify:
            for candidate in candidates[:20]:  # Limit to top 20 to avoid too many requests
                if candidate not in seen_emails:
                    seen_emails.add(candidate)
                    verified_email, score = verify_email(candidate)
                    if verified_email and score > 0.3:  # Only include emails with decent score
                        # Optionally check SMTP if requested
                        if check_smtp:
                            email_domain = verified_email.split('@')[1] if '@' in verified_email else domain
                            has_mx, smtp_reachable = check_email_server_reachable(email_domain)
                            if smtp_reachable:
                                score = min(score + 0.1, 1.0)
                                logger.debug(f"   SMTP check passed for {verified_email}, boosted score")
                        
                        email_scores.append((verified_email, score))
                        logger.debug(f"   ✓ Verified candidate: {verified_email} (score: {score:.2f})")
        else:
            # Just add candidates without verification
            for candidate in candidates[:20]:
                if candidate not in seen_emails:
                    seen_emails.add(candidate)
                    email_scores.append((candidate, 0.5))  # Default score
    
    # Sort by score descending
    email_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Return best match (highest score) or all if multiple
    if email_scores:
        best_email, best_score = email_scores[0]
        logger.info(f"   ✅ Found {len(email_scores)} verified emails (best: {best_email} with score {best_score:.2f})")
    else:
        logger.warning(f"   ✗ No valid emails found for domain: {domain}")
    
    return email_scores

