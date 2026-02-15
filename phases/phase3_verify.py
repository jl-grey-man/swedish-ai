"""
Phase 3: VERIFY — Deterministic. No LLM.
Checks every extracted signal against raw source data.
Drops anything that can't be verified.
"""

import json
import logging
import re
import time
from difflib import SequenceMatcher

import requests

from database import get_db

log = logging.getLogger("verify")

# Allabolag.se scraping for company verification
ALLABOLAG_SEARCH = "https://www.allabolag.se/what/{}"
VERIFY_TIMEOUT = 10


def fuzzy_match(quote: str, source_text: str, threshold: float = 0.65) -> tuple:
    """
    Check if a quote exists in the source text.
    Returns (passed: bool, similarity: float).
    
    Uses sliding window to find best match since the quote
    might be a substring of the larger text.
    """
    if not quote or not source_text:
        return False, 0.0
    
    quote_clean = re.sub(r'\s+', ' ', quote.strip().lower())
    source_clean = re.sub(r'\s+', ' ', source_text.strip().lower())
    
    # Quick check: exact substring
    if quote_clean in source_clean:
        return True, 1.0
    
    # Sliding window fuzzy match
    quote_len = len(quote_clean)
    best_ratio = 0.0
    
    # Step through source in chunks roughly the size of the quote
    step = max(1, quote_len // 4)
    for i in range(0, len(source_clean) - quote_len + 1, step):
        window = source_clean[i:i + quote_len + 50]  # Slight overshoot
        ratio = SequenceMatcher(None, quote_clean, window).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
        if ratio >= threshold:
            return True, ratio
    
    # Also check with shorter windows for partial quotes
    if len(quote_clean) > 50:
        # Check first half and second half independently
        half = len(quote_clean) // 2
        first_half = quote_clean[:half]
        second_half = quote_clean[half:]
        
        first_found = first_half in source_clean
        second_found = second_half in source_clean
        
        if first_found and second_found:
            return True, 0.85
        elif first_found or second_found:
            return True, 0.70
    
    return best_ratio >= threshold, best_ratio


def check_url_alive(url: str) -> str:
    """Check if URL is still accessible. Returns status string."""
    try:
        resp = requests.head(url, timeout=VERIFY_TIMEOUT, allow_redirects=True)
        if resp.status_code == 200:
            return "live"
        elif resp.status_code in (301, 302, 307, 308):
            return "redirect"
        elif resp.status_code in (403, 401):
            return "live"  # Exists but restricted — still valid
        elif resp.status_code == 404:
            return "dead"
        else:
            return "live"  # Assume alive for other codes
    except requests.RequestException:
        return "timeout"


def verify_company_allabolag(company_name: str) -> dict:
    """
    Look up company on Allabolag.se.
    Returns enrichment data or empty dict.
    
    NOTE: This is basic scraping. Allabolag might block
    heavy usage. Rate limit accordingly.
    """
    if not company_name:
        return {}
    
    try:
        url = ALLABOLAG_SEARCH.format(requests.utils.quote(company_name))
        resp = requests.get(url, timeout=VERIFY_TIMEOUT, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        })
        
        if resp.status_code != 200:
            return {}
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Look for first search result
        result = soup.select_one("a.search-result-item, div.company-info")
        if not result:
            return {}
        
        # Try to extract basic info
        data = {
            "found": True,
            "search_url": url,
        }
        
        # Extract org number, revenue, employees if visible
        text = result.get_text(" ", strip=True)
        
        org_match = re.search(r'(\d{6}-\d{4})', text)
        if org_match:
            data["org_number"] = org_match.group(1)
        
        return data
        
    except Exception as e:
        log.debug(f"Allabolag lookup failed for '{company_name}': {e}")
        return {}


def check_duplicate(conn, signal) -> tuple:
    """
    Check if this signal is a duplicate of an existing one.
    Returns (is_duplicate: bool, duplicate_id: int or None).
    """
    # Same person + same company + similar topic within 7 days
    person = signal.get("person_name")
    company = signal.get("company_name") or signal.get("person_company")
    
    if not person and not company:
        return False, None
    
    conditions = []
    params = []
    
    if person:
        conditions.append("es.person_name = ?")
        params.append(person)
    if company:
        conditions.append("(es.company_name = ? OR es.person_company = ?)")
        params.extend([company, company])
    
    where = " AND ".join(conditions)
    
    rows = conn.execute(f"""
        SELECT es.id, es.original_quote
        FROM extracted_signals es
        JOIN verified_signals vs ON vs.signal_id = es.id
        WHERE {where}
        AND vs.final_status = 'verified'
        AND es.created_at >= datetime('now', '-7 days')
    """, params).fetchall()
    
    if not rows:
        return False, None
    
    # Check if the quote is similar to any existing
    quote = signal.get("original_quote", "")
    for row in rows:
        existing_quote = row["original_quote"] or ""
        if quote and existing_quote:
            ratio = SequenceMatcher(None, quote.lower(), 
                                   existing_quote.lower()).ratio()
            if ratio > 0.7:
                return True, row["id"]
    
    return False, None


def run_verification(conn):
    """
    Main verification pass.
    Processes all unverified extracted signals.
    """
    # Get signals that haven't been verified yet
    unverified = conn.execute("""
        SELECT es.id, es.source_hash, es.original_quote,
               es.company_name, es.person_company, es.person_name,
               rc.source_url, rc.raw_text
        FROM extracted_signals es
        JOIN raw_crawl rc ON rc.source_hash = es.source_hash
        LEFT JOIN verified_signals vs ON vs.signal_id = es.id
        WHERE vs.id IS NULL
    """).fetchall()
    
    log.info(f"Verifying {len(unverified)} signals")
    
    stats = {"verified": 0, "rejected": 0, "weak": 0, "duplicates": 0}
    
    for signal in unverified:
        signal_id = signal["id"]
        quote = signal["original_quote"] or ""
        source_text = signal["raw_text"] or ""
        url = signal["source_url"]
        company = signal["company_name"] or signal["person_company"]
        
        # 1. Quote check
        quote_passed, quote_sim = fuzzy_match(quote, source_text)
        quote_status = "passed" if quote_passed else (
            "partial" if quote_sim > 0.5 else "failed"
        )
        
        # 2. URL check
        url_status = check_url_alive(url)
        time.sleep(0.5)  # Rate limit
        
        # 3. Company check (if applicable)
        company_verified = 0
        allabolag_data = {}
        if company:
            allabolag_data = verify_company_allabolag(company)
            company_verified = 1 if allabolag_data.get("found") else 0
            time.sleep(1.0)  # Rate limit Allabolag
        
        # 4. Duplicate check
        is_dup, dup_id = check_duplicate(conn, dict(signal))
        if is_dup:
            stats["duplicates"] += 1
        
        # Determine final status
        if quote_status == "failed":
            final_status = "rejected"
            stats["rejected"] += 1
        elif url_status == "dead":
            final_status = "rejected"
            stats["rejected"] += 1
        elif quote_status == "partial" or url_status == "timeout":
            final_status = "weak"
            stats["weak"] += 1
        else:
            final_status = "verified"
            stats["verified"] += 1
        
        # Store verification result
        conn.execute("""
            INSERT INTO verified_signals
            (signal_id, quote_check, quote_similarity, url_check,
             company_verified, company_allabolag_data, is_duplicate,
             duplicate_of, final_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal_id, quote_status, quote_sim, url_status,
            company_verified, json.dumps(allabolag_data, ensure_ascii=False),
            1 if is_dup else 0, dup_id, final_status
        ))
    
    conn.commit()
    log.info(f"Verification complete: {json.dumps(stats)}")
    return stats


if __name__ == "__main__":
    conn = get_db()
    run_verification(conn)
    conn.close()
