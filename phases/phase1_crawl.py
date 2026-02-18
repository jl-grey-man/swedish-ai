"""
Phase 1: CRAWL — Tavily search engine.
No LLM. Pure search + content retrieval. Deterministic.

Searches via Tavily API, fetches result content,
stores raw content in SQLite.
"""

import json
import re
import time
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from tavily import TavilyClient

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

# Tavily config
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "").strip()
if not TAVILY_API_KEY:
    # Try loading from config file
    config_file = Path(__file__).parent.parent / "config" / "api_keys.json"
    if config_file.exists():
        with open(config_file) as f:
            TAVILY_API_KEY = json.load(f).get("tavily", "")

if not TAVILY_API_KEY:
    raise RuntimeError(
        "TAVILY_API_KEY not set. Set env var or add to config/api_keys.json"
    )

tavily = TavilyClient(api_key=TAVILY_API_KEY)

# Rate limiting — Tavily is API-based so lighter limits
QUERY_DELAY = 1.0  # seconds between Tavily calls (be polite)

# Domains to skip (not useful content)
SKIP_DOMAINS = {
    "google.com", "google.se", "youtube.com", "facebook.com",
    "instagram.com", "twitter.com", "x.com", "tiktok.com",
    "pinterest.com", "wikipedia.org", "amazon.se", "amazon.com",
}


def search_tavily(query: str, include_domains: list[str] = None,
                  max_results: int = 5) -> list[dict]:
    """
    Search via Tavily API. Returns list of results with content.
    Tavily returns extracted text directly — no need to fetch pages.
    """
    try:
        kwargs = {
            "query": query,
            "max_results": max_results,
            "search_depth": "advanced",
            "include_answer": False,
        }
        if include_domains:
            kwargs["include_domains"] = include_domains

        response = tavily.search(**kwargs)
        results = []

        for r in response.get("results", []):
            url = r.get("url", "")
            domain = urlparse(url).netloc.replace("www.", "")

            if domain in SKIP_DOMAINS:
                continue

            content = r.get("content", "")
            raw_content = r.get("raw_content", "")

            results.append({
                "url": url,
                "domain": domain,
                "title": r.get("title", ""),
                "snippet": content,
                "raw_text": raw_content if raw_content else content,
            })

        log.info(f"Query '{query[:60]}' returned {len(results)} results")
        return results

    except Exception as e:
        log.warning(f"Tavily search failed for '{query}': {e}")
        return []


def extract_date_from_text(text: str) -> str:
    """Try to find a date in the page content."""
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
    Main crawl execution. Generates queries, searches via Tavily,
    stores everything.
    """
    init_db()
    conn = get_db()

    queries = generate_run_queries(conn)

    stats = {
        "queries_run": 0,
        "results_found": 0,
        "pages_stored": 0,
        "duplicates": 0,
        "errors": 0,
    }

    log.info(f"Starting Tavily crawl with {len(queries)} queries")

    for i, q in enumerate(queries):
        query_text = q["query"]
        keyword_type = q["type"]
        site = q["site"]
        include_domains = q.get("include_domains")

        log.info(f"[{i+1}/{len(queries)}] [{keyword_type}] {query_text[:70]}")

        # Search via Tavily
        results = search_tavily(
            query_text,
            include_domains=include_domains,
            max_results=5
        )
        stats["queries_run"] += 1
        stats["results_found"] += len(results)

        # Log the query
        log_query(conn, query_text, keyword_type, site, len(results))

        # Store each result (Tavily already provides content)
        for result in results:
            url = result["url"]
            domain = result["domain"]

            # Check if already crawled
            existing = conn.execute(
                "SELECT 1 FROM raw_crawl WHERE source_url = ?", (url,)
            ).fetchone()
            if existing:
                stats["duplicates"] += 1
                continue

            raw_text = result["raw_text"]
            if len(raw_text) < 50:
                continue

            content_date = extract_date_from_text(raw_text)
            source_hash = store_crawl_result(
                conn=conn,
                url=url,
                domain=domain,
                title=result["title"],
                raw_text=raw_text,
                raw_html="",  # Tavily doesn't return HTML
                query=query_text,
                keyword_type=keyword_type,
                http_status=200,
                content_date=content_date,
            )

            if source_hash:
                stats["pages_stored"] += 1
                log.info(f"  Stored: {url[:80]} [{source_hash}]")
            else:
                stats["duplicates"] += 1

        # Small delay between Tavily calls
        if i < len(queries) - 1:
            time.sleep(QUERY_DELAY)

    # Save run stats
    stats_file = DATA_DIR / "logs" / f"crawl_stats_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=2)

    log.info(f"Crawl complete: {json.dumps(stats, indent=2)}")
    conn.close()
    return stats


if __name__ == "__main__":
    run_crawl()
