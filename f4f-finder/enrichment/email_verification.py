import re
import socket
import smtplib
from typing import Optional, Tuple
import httpx
import dns.resolver
from utils.logger import logger

# Email regex pattern for basic validation
EMAIL_PATTERN = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

# Disposable email domains (common ones)
DISPOSABLE_EMAIL_DOMAINS = {
    'tempmail.com', '10minutemail.com', 'guerrillamail.com',
    'mailinator.com', 'throwaway.email', 'temp-mail.org'
}

# Well-known email providers that are reliable even if SMTP connection fails
WELL_KNOWN_EMAIL_PROVIDERS = {
    'gmail.com', 'googlemail.com',
    'outlook.com', 'hotmail.com', 'live.com', 'msn.com',
    'yahoo.com', 'yahoo.co.uk', 'yahoo.fr', 'yahoo.de',
    'aol.com', 'icloud.com', 'me.com', 'mac.com',
    'protonmail.com', 'proton.me', 'zoho.com',
    'mail.com', 'gmx.com', 'yandex.com'
}


def check_domain_exists(domain: str) -> bool:
    """
    Check if domain exists by performing DNS lookup.
    
    Args:
        domain: Domain name to check
        
    Returns:
        True if domain exists, False otherwise
    """
    try:
        logger.info(f"  ✓ Checking if domain '{domain}' exists (DNS lookup)...")
        socket.gethostbyname(domain)
        logger.info(f"  ✓ Domain '{domain}' exists")
        return True
    except (socket.gaierror, socket.herror):
        logger.info(f"  ✗ Domain '{domain}' does not exist (DNS lookup failed)")
        return False


def check_domain_active(domain: str) -> bool:
    """
    Check if domain is active by attempting HTTP/HTTPS connection.
    
    Args:
        domain: Domain name to check
        
    Returns:
        True if domain is active, False otherwise
    """
    try:
        logger.info(f"  ✓ Checking if domain '{domain}' is active (HTTP/HTTPS)...")
        # Try HTTPS first, then HTTP
        for protocol in ['https', 'http']:
            try:
                url = f"{protocol}://{domain}"
                with httpx.Client(timeout=5.0) as client:
                    response = client.get(url, follow_redirects=True)
                    if response.status_code < 500:  # Any non-server-error response indicates domain is active
                        logger.info(f"  ✓ Domain '{domain}' is active (responded via {protocol.upper()})")
                        return True
            except (httpx.RequestError, httpx.TimeoutException):
                continue
        logger.info(f"  ✗ Domain '{domain}' is not active (no HTTP/HTTPS response)")
        return False
    except Exception as e:
        logger.info(f"  ✗ Error checking domain activity for '{domain}': {e}")
        return False


def check_email_server_reachable(domain: str) -> Tuple[bool, bool]:
    """
    Check if email server can be reached by checking MX records and attempting SMTP connection.
    
    Args:
        domain: Domain name to check
        
    Returns:
        Tuple of (has_mx_records, smtp_reachable) where:
        - has_mx_records: True if MX records exist
        - smtp_reachable: True if SMTP connection succeeded
    """
    has_mx = False
    smtp_reachable = False
    mx_record = None
    
    try:
        logger.info(f"  ✓ Checking if email server for '{domain}' is reachable (MX records + SMTP)...")
        # Check for MX records
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            if not mx_records:
                logger.info(f"  ✗ No MX records found for domain '{domain}'")
                return False, False
            
            # Get the first MX record (highest priority)
            mx_record = str(mx_records[0].exchange).rstrip('.')
            has_mx = True
            logger.info(f"  ✓ Found MX record for '{domain}': {mx_record}")
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            logger.info(f"  ✗ Could not resolve MX records for domain '{domain}'")
            return False, False
        
        # Try to connect to SMTP server (without sending email)
        try:
            smtp = smtplib.SMTP(timeout=5)
            smtp.connect(mx_record, 25)
            smtp.quit()
            smtp_reachable = True
            logger.info(f"  ✓ Email server '{mx_record}' is reachable via SMTP")
        except (smtplib.SMTPException, socket.error, socket.timeout) as e:
            logger.info(f"  ⚠ Could not connect to email server '{mx_record}' via SMTP: {e}")
            logger.info(f"    (This is common - many providers block port 25 for security)")
            smtp_reachable = False
            
    except Exception as e:
        logger.info(f"  ✗ Error checking email server reachability for '{domain}': {e}")
        return has_mx, False
    
    return has_mx, smtp_reachable


def verify_email(email: Optional[str]) -> Tuple[Optional[str], float]:
    """
    Verify email address and return a confidence score.
    Performs multiple checks:
    1. Email format validation
    2. Domain existence check (DNS lookup)
    3. Domain activity check (HTTP/HTTPS)
    4. Email server reachability check (MX records and SMTP)
    
    Args:
        email: Email address to verify
        
    Returns:
        Tuple of (email, score) where:
        - email: The email if valid, None if invalid
        - score: Confidence score from 0.0 to 1.0
    """
    if not email:
        logger.info("Email verification: No email provided")
        return None, 0.0
    
    email = email.strip().lower()
    logger.info(f"\n📧 Verifying email: {email}")
    
    # 1. Check email format
    logger.info("  ✓ Checking email format...")
    if not EMAIL_PATTERN.match(email):
        logger.info(f"  ✗ Email '{email}' failed format validation")
        return None, 0.0
    logger.info("  ✓ Email format is valid")
    score = 0.2  # Base score for valid format
    logger.info(f"    Score: {score:.2f} (valid format)")
    
    # Extract domain
    domain = email.split('@')[1] if '@' in email else ''
    
    # Check for disposable email domains
    if domain in DISPOSABLE_EMAIL_DOMAINS:
        logger.info(f"  ✗ Email '{email}' is from disposable domain '{domain}'")
        logger.info(f"    Final email score: 0.10 (disposable domain)")
        return email, 0.1  # Very low score for disposable emails
    
    # Additional validation checks
    # Check for common typos or suspicious patterns
    if '..' in email or email.startswith('.') or email.endswith('.'):
        logger.info(f"  ✗ Email '{email}' has suspicious pattern")
        logger.info(f"    Final email score: 0.15 (suspicious pattern)")
        return email, 0.15
    
    # Check domain has valid TLD
    parts = domain.split('.')
    if len(parts) < 2:
        logger.info(f"  ✗ Domain '{domain}' has invalid TLD")
        return None, 0.0
    
    # 2. Check if domain exists
    if check_domain_exists(domain):
        score += 0.2
        logger.info(f"    Score: {score:.2f} (+0.20 for domain existence)")
    else:
        logger.info(f"    Final email score: {score:.2f} (domain does not exist)")
        return email, score  # Return early with low score if domain doesn't exist
    
    # 3. Check if domain is active
    if check_domain_active(domain):
        score += 0.2
        logger.info(f"    Score: {score:.2f} (+0.20 for domain activity)")
    else:
        logger.info(f"    Score: {score:.2f} (domain not active, no points added)")
        # Don't return early, continue with other checks
    
    # 4. Check if email server can be reached
    has_mx_records, smtp_reachable = check_email_server_reachable(domain)
    
    if smtp_reachable:
        # Full points if SMTP connection works
        score += 0.4
        logger.info(f"    Score: {score:.2f} (+0.40 for email server reachability)")
    elif has_mx_records:
        # Partial points if MX records exist but SMTP connection fails
        # This is common for well-known providers that block port 25
        if domain in WELL_KNOWN_EMAIL_PROVIDERS:
            score += 0.35  # Almost full points for well-known providers
            logger.info(f"    Score: {score:.2f} (+0.35 for MX records + well-known provider)")
        else:
            score += 0.25  # Partial points for other domains with MX records
            logger.info(f"    Score: {score:.2f} (+0.25 for MX records, SMTP blocked)")
    else:
        logger.info(f"    Score: {score:.2f} (no MX records, no points added)")
        # Don't return early, but reduce score
    
    # Cap score at 1.0
    score = min(score, 1.0)
    logger.info(f"  ✓ Final email score: {score:.2f}")
    
    return email, round(score, 2)
