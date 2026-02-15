"""
Phase 1: CRAWL — Google dorking engine.
No LLM. Pure scraping. Deterministic.

Searches Google with generated queries, fetches result pages,
stores raw content in SQLite.
"""

import json
import random
import re
import time
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, quote_plus

import requests
from bs4 import BeautifulSoup

from database import get_db, init_db, store_crawl_result, log_query
from query_builder import generate_run_queries

# --- Config ---
DATA_DIR = Path(__file__).parent.parent / "data"
LOG_DIR = Path(__file__).parent.parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "crawl.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("crawl")

# Rate limiting
MIN_DELAY = 2.0   # seconds between Google searches
MAX_DELAY = 5.0   # randomized to avoid patterns
PAGE_FETCH_DELAY = 1.0  # seconds between fetching result pages

# Request settings
HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) "
                       "Gecko/20100101 Firefox/121.0",
        "Accept-Language": "sv-SE,sv;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
]

# Domains to skip (not useful content)
SKIP_DOMAINS = {
    "google.com", "google.se", "youtube.com", "facebook.com",
    "instagram.com", "twitter.com", "x.com", "tiktok.com",
    "pinterest.com", "wikipedia.org", "amazon.se", "amazon.com",
}

SESSION = requests.Session()


def get_headers():
    return random.choice(HEADERS_LIST)


def search_google(query: str, num_results: int = 10) -> list[dict]:
    """
    Search Google and return list of result URLs with snippets.
    Uses google.se for Swedish results.
    """
    encoded = quote_plus(query)
    url = f"https://www.google.se/search?q={encoded}&num={num_results}&hl=sv"
    
    try:
        resp = SESSION.get(url, headers=get_headers(), timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning(f"Google search failed for '{query}': {e}")
        return []
    
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    
    for g in soup.select("div.g"):
        link_el = g.select_one("a[href]")
        snippet_el = g.select_one("div.VwiC3b") or g.select_one("span.st")
        
        if not link_el:
            continue
            
        href = link_el.get("href", "")
        if not href.startswith("http"):
            continue
            
        domain = urlparse(href).netloc.replace("www.", "")
        if domain in SKIP_DOMAINS:
            continue
        
        title = link_el.get_text(strip=True)
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        
        results.append({
            "url": href,
            "domain": domain,
            "title": title,
            "snippet": snippet,
        })
    
    # Fallback: try extracting from different Google result format
    if not results:
        for a_tag in soup.find_all("a"):
            href = a_tag.get("href", "")
            if href.startswith("/url?q="):
                clean_url = href.split("/url?q=")[1].split("&")[0]
                domain = urlparse(clean_url).netloc.replace("www.", "")
                if domain not in SKIP_DOMAINS and clean_url.startswith("http"):
                    results.append({
                        "url": clean_url,
                        "domain": domain,
                        "title": a_tag.get_text(strip=True),
                        "snippet": "",
                    })
    
    log.info(f"Query '{query[:60]}...' returned {len(results)} results")
    return results


def fetch_page(url: str) -> dict:
    """
    Fetch a page and extract clean text content.
    Returns dict with raw_text, raw_html, title, status.
    """
    try:
        resp = SESSION.get(url, headers=get_headers(), timeout=15, 
                          allow_redirects=True)
        status = resp.status_code
        
        if status != 200:
            return {"raw_text": "", "raw_html": "", "title": "", 
                    "status": status, "error": f"HTTP {status}"}
        
        # Check content type
        ctype = resp.headers.get("content-type", "")
        if "text/html" not in ctype and "text/plain" not in ctype:
            return {"raw_text": "", "raw_html": "", "title": "",
                    "status": status, "error": f"Not HTML: {ctype}"}
        
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script, style, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header", 
                         "aside", "noscript"]):
            tag.decompose()
        
        title = soup.title.get_text(strip=True) if soup.title else ""
        
        # Get main content — try article first, then body
        main = soup.find("article") or soup.find("main") or soup.find("body")
        raw_text = main.get_text(separator="\n", strip=True) if main else ""
        
        # Truncate extremely long pages
        if len(raw_text) > 50000:
            raw_text = raw_text[:50000] + "\n[TRUNCATED]"
        
        return {
            "raw_text": raw_text,
            "raw_html": html[:100000],  # Keep HTML but cap size
            "title": title,
            "status": status,
            "error": None,
        }
        
    except requests.RequestException as e:
        log.warning(f"Failed to fetch {url}: {e}")
        return {"raw_text": "", "raw_html": "", "title": "",
                "status": 0, "error": str(e)}


def extract_date_from_text(text: str) -> str:
    """Try to find a date in the page content."""
    # Common Swedish date patterns
    patterns = [
        r'(\d{4}-\d{2}-\d{2})',  # 2024-12-15
        r'(\d{1,2}\s+(?:jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)\w*\s+\d{4})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text[:2000], re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def run_crawl():
    """
    Main crawl execution. Generates queries, searches Google,
    fetches pages, stores everything.
    """
    init_db()
    conn = get_db()
    
    queries = generate_run_queries(conn)
    
    stats = {
        "queries_run": 0,
        "results_found": 0,
        "pages_fetched": 0,
        "pages_stored": 0,
        "duplicates": 0,
        "errors": 0,
    }
    
    log.info(f"Starting crawl with {len(queries)} queries")
    
    for i, q in enumerate(queries):
        query_text = q["query"]
        keyword_type = q["type"]
        site = q["site"]
        
        log.info(f"[{i+1}/{len(queries)}] [{keyword_type}] {query_text[:70]}")
        
        # Search Google
        results = search_google(query_text)
        stats["queries_run"] += 1
        stats["results_found"] += len(results)
        
        # Log the query
        log_query(conn, query_text, keyword_type, site, len(results))
        
        # Fetch each result page
        for result in results[:5]:  # Max 5 pages per query
            url = result["url"]
            domain = result["domain"]
            
            # Check if already crawled
            existing = conn.execute(
                "SELECT 1 FROM raw_crawl WHERE source_url = ?", (url,)
            ).fetchone()
            if existing:
                stats["duplicates"] += 1
                continue
            
            time.sleep(PAGE_FETCH_DELAY)
            page = fetch_page(url)
            
            if page["error"] or len(page["raw_text"]) < 100:
                stats["errors"] += 1 if page["error"] else 0
                continue
            
            stats["pages_fetched"] += 1
            
            # Store in database
            content_date = extract_date_from_text(page["raw_text"])
            source_hash = store_crawl_result(
                conn=conn,
                url=url,
                domain=domain,
                title=page["title"] or result["title"],
                raw_text=page["raw_text"],
                raw_html=page["raw_html"],
                query=query_text,
                keyword_type=keyword_type,
                http_status=page["status"],
                content_date=content_date,
            )
            
            if source_hash:
                stats["pages_stored"] += 1
                log.info(f"  Stored: {url[:80]} [{source_hash}]")
            else:
                stats["duplicates"] += 1
        
        # Delay between Google searches
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)
        
        # Check for Google blocking (CAPTCHA detection)
        if stats["queries_run"] % 20 == 0 and stats["results_found"] == 0:
            log.warning("No results in last batch — possible rate limit. "
                       "Pausing 60 seconds.")
            time.sleep(60)
    
    # Save run stats
    stats_file = DATA_DIR / "logs" / f"crawl_stats_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=2)
    
    log.info(f"Crawl complete: {json.dumps(stats, indent=2)}")
    conn.close()
    return stats


if __name__ == "__main__":
    run_crawl()
