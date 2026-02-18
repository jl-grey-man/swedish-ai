"""
Phase 2.5: Source Credibility Check
Deterministic + LLM hybrid to detect sales pitches and sponsored content.
"""

import json
import logging
import re
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database import get_db

log = logging.getLogger("credibility")


def deterministic_credibility_check(url: str, html: str) -> dict:
    """
    Fast pattern matching for obvious red flags.
    No LLM needed - pure regex.
    
    Returns:
        dict with auto_reject, red_flags, and optional scores
    """
    red_flags = []
    auto_reject = False
    
    if not html:
        html = ""
    
    # Sponsored content markers (Swedish and English)
    sponsored_patterns = [
        r'brand\s*studio',
        r'i\s+samarbete\s+med',
        r'annons(?:ering)?',
        r'sponsored',
        r'paid\s+partnership',
        r'in\s+cooperation\s+with',
        r'producerad\s+av.*i\s+samarbete',
        r'partnership\s+content',
        r'native\s+advertising',
        r'betalt\s+innehåll',
        r'reklam',
    ]
    
    for pattern in sponsored_patterns:
        if re.search(pattern, html, re.IGNORECASE):
            red_flags.append(f"sponsored_marker: {pattern}")
            auto_reject = True
    
    # URL patterns
    url_red_flags = [
        '/brandstudio/', '/annons/', '/sponsored/', 
        '/partners/', '/native-ads/', '/reklam/'
    ]
    for flag in url_red_flags:
        if flag in url.lower():
            red_flags.append(f"url_contains: {flag}")
            auto_reject = True
    
    # Geographic check (Nordic countries only)
    nordic_tlds = ['.se', '.dk', '.no', '.fi', '.is']
    nordic_domains = ['sweden', 'sverige', 'denmark', 'danmark', 
                     'norway', 'norge', 'finland', 'suomi', 'iceland',
                     'ísland']
    
    is_nordic = False
    
    # Check TLDs
    if any(tld in url for tld in nordic_tlds):
        is_nordic = True
    
    # Check domains
    if any(dom in url.lower() for dom in nordic_domains):
        is_nordic = True
    
    # Check LinkedIn country codes
    if 'linkedin.com' in url:
        nordic_linkedin = ['se.linkedin', 'dk.linkedin', 'no.linkedin',
                          'fi.linkedin', 'is.linkedin']
        is_nordic = any(nl in url for nl in nordic_linkedin)
        
        # Also check for Swedish translation parameter
        if '?tl=sv' in url or '&tl=sv' in url:
            is_nordic = True
    
    # Check Reddit for Nordic subreddits
    if 'reddit.com' in url:
        nordic_subs = ['/sweden', '/norge', '/denmark', '/suomi', 
                      '/iceland', '/foretagande']
        is_nordic = any(sub in url.lower() for sub in nordic_subs)
    
    if not is_nordic:
        red_flags.append("non_nordic_geography")
        # Don't auto-reject yet, let LLM check if content is still Swedish
    
    return {
        "auto_reject": auto_reject,
        "red_flags": red_flags,
        "sales_intent_score": 10 if auto_reject else None,
        "objectivity_score": 10 if auto_reject else None,
        "is_nordic": is_nordic
    }


def run_credibility_check(conn, limit=100):
    """
    Main entry point - deterministic check for now.
    LLM check can be added later for ambiguous cases.
    """
    
    # Get signals without credibility check
    unchecked = conn.execute("""
        SELECT es.id, es.source_hash, rc.source_url, rc.raw_html
        FROM extracted_signals es
        JOIN raw_crawl rc ON rc.source_hash = es.source_hash
        LEFT JOIN credibility_scores cs ON cs.signal_id = es.id
        WHERE cs.id IS NULL
        LIMIT ?
    """, (limit,)).fetchall()
    
    log.info(f"Checking credibility for {len(unchecked)} signals")
    
    stats = {
        "rejected": 0,
        "accepted": 0,
        "review": 0
    }
    
    for row in unchecked:
        check = deterministic_credibility_check(
            url=row["source_url"],
            html=row["raw_html"] or ""
        )
        
        if check["auto_reject"]:
            verdict = "reject"
            stats["rejected"] += 1
            reasoning = f"Auto-rejected: {', '.join(check['red_flags'])}"
        elif not check["is_nordic"]:
            verdict = "review"  # Let human decide on non-Nordic content
            stats["review"] += 1
            reasoning = "Non-Nordic source, needs manual review"
        else:
            verdict = "accept"
            stats["accepted"] += 1
            reasoning = "Deterministic checks passed"
        
        # Store result
        conn.execute("""
            INSERT INTO credibility_scores
            (signal_id, sales_intent_score, objectivity_score,
             sponsored_content, detected_patterns, reasoning,
             language, verdict)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["id"],
            check.get("sales_intent_score") or 5,
            check.get("objectivity_score") or 5,
            check["auto_reject"],
            json.dumps(check["red_flags"]),
            reasoning,
            "unknown",  # Language detection can be added later
            verdict
        ))
    
    conn.commit()
    log.info(f"Credibility check complete: {stats}")
    return stats


if __name__ == "__main__":
    from database import init_db
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    init_db()
    conn = get_db()
    
    try:
        stats = run_credibility_check(conn)
        print(f"\n✓ Credibility check complete:")
        print(f"  Accepted: {stats['accepted']}")
        print(f"  Review: {stats['review']}")
        print(f"  Rejected: {stats['rejected']}")
    finally:
        conn.close()
