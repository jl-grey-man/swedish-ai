"""
Query Builder — Generates search queries with 66/34 core/discovery split.
Handles rotation, deduplication, and keyword combination logic.

Generates natural-language Swedish queries for Tavily search.
Uses include_domains for site targeting instead of site: operator.
"""

import json
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from itertools import product as iter_product

CONFIG_DIR = Path(__file__).parent.parent / "config"

# Map site keys to actual domains for Tavily include_domains
SITE_DOMAINS = {
    "linkedin": ["linkedin.com"],
    "linkedin_articles": ["linkedin.com"],
    "foretagarna": ["foretagarna.se"],
    "breakit": ["breakit.se"],
    "di": ["di.se"],
    "nyteknik": ["nyteknik.se"],
    "flashback": ["flashback.org"],
    "reddit_sweden": ["reddit.com"],
    "reddit_foretagande": ["reddit.com"],
    "general_swedish": [],  # No domain restriction — open web
    "nordic_business": ["breakit.se", "di.se", "nyteknik.se", "foretagarna.se"],
    "forums": ["reddit.com", "flashback.org"],
}


def load_keywords():
    with open(CONFIG_DIR / "keywords.json", "r") as f:
        return json.load(f)


def get_recent_queries(conn, days=3):
    """Get queries used in the last N days to avoid repeats."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')
    rows = conn.execute(
        "SELECT query_text FROM query_log WHERE run_date >= ?", (cutoff,)
    ).fetchall()
    return {row[0] for row in rows}


def get_keyword_performance(conn):
    """Get hit rates for discovery keywords to weight selection."""
    rows = conn.execute("""
        SELECT keyword, hit_rate, times_used
        FROM keyword_history
        WHERE active = 1 AND keyword_type = 'discovery'
    """).fetchall()
    return {row[0]: {"hit_rate": row[1], "times_used": row[2]} for row in rows}


def build_core_queries(keywords, site_targets, count):
    """
    Build the 66% — natural language queries from known pain terms.

    Patterns (in Swedish, natural language for Tavily):
    1. pain + business context (open web)
    2. pain + specific task (domain-targeted)
    3. AI awareness + business context (domain-targeted)
    4. Single strong pain term (open web, Swedish)
    """
    queries = []

    pain = keywords["core_keywords"]["pain_signals"]
    ai = keywords["core_keywords"]["ai_awareness"]
    biz = keywords["core_keywords"]["business_context"]
    tasks = keywords["core_keywords"]["specific_tasks"]

    # Pattern 1: pain + biz context — open web Swedish
    for p in pain:
        for b in biz:
            queries.append({
                "query": f"{p} {b} Sverige",
                "type": "core",
                "site": "general_swedish",
                "include_domains": None,
                "keywords_used": [p, b]
            })

    # Pattern 2: specific task + pain — targeted to business sites
    for t in tasks:
        for p in random.sample(pain, min(4, len(pain))):
            site_key = random.choice(["nordic_business", "general_swedish"])
            queries.append({
                "query": f"{t} {p} företag",
                "type": "core",
                "site": site_key,
                "include_domains": SITE_DOMAINS.get(site_key),
                "keywords_used": [t, p]
            })

    # Pattern 3: AI + biz — targeted to tech/business press
    for a in ai:
        for b in biz:
            site_key = random.choice(
                ["nordic_business", "linkedin", "general_swedish"]
            )
            queries.append({
                "query": f"{a} {b}",
                "type": "core",
                "site": site_key,
                "include_domains": SITE_DOMAINS.get(site_key),
                "keywords_used": [a, b]
            })

    # Pattern 4: pain + task — forums
    for p in pain:
        for t in random.sample(tasks, min(3, len(tasks))):
            queries.append({
                "query": f"{p} {t}",
                "type": "core",
                "site": "forums",
                "include_domains": SITE_DOMAINS.get("forums"),
                "keywords_used": [p, t]
            })

    # Shuffle and limit
    random.shuffle(queries)
    return queries[:count]


def build_discovery_queries(keywords, site_targets, count, performance=None):
    """
    Build the 34% — exploratory queries from LLM-suggested and adjacent terms.
    More natural language, broader searches.
    """
    queries = []

    discovery = keywords["discovery_keywords"]
    from_signals = discovery.get("from_signals", [])
    adjacent = discovery.get("adjacent_terms", [])
    biz = keywords["core_keywords"]["business_context"]

    all_discovery = from_signals + adjacent
    if not all_discovery:
        return []

    # Weight by performance if we have data
    if performance:
        weighted = []
        for kw in all_discovery:
            perf = performance.get(kw, {})
            if perf.get("times_used", 0) == 0:
                weight = 1.5
            elif perf.get("hit_rate", 0) > 0:
                weight = 1.0 + perf["hit_rate"]
            else:
                weight = 0.3
            weighted.extend([kw] * max(1, int(weight * 3)))
        all_discovery = weighted

    # Pattern 1: discovery term + business context — open web
    for kw in all_discovery:
        b = random.choice(biz)
        queries.append({
            "query": f"{kw} {b} Sverige",
            "type": "discovery",
            "site": "general_swedish",
            "include_domains": None,
            "keywords_used": [kw, b]
        })

    # Pattern 2: discovery term alone — forums
    for kw in all_discovery:
        queries.append({
            "query": f"{kw} företag",
            "type": "discovery",
            "site": "forums",
            "include_domains": SITE_DOMAINS.get("forums"),
            "keywords_used": [kw]
        })

    # Pattern 3: discovery term — business press
    for kw in all_discovery:
        queries.append({
            "query": f"{kw} svensk företag",
            "type": "discovery",
            "site": "nordic_business",
            "include_domains": SITE_DOMAINS.get("nordic_business"),
            "keywords_used": [kw]
        })

    random.shuffle(queries)
    return queries[:count]


def generate_run_queries(conn):
    """
    Main entry point. Generates the full query set for one run.
    Returns list of query dicts ready for the crawler.
    """
    keywords = load_keywords()
    rotation = keywords["rotation"]

    total = rotation["queries_per_run"]
    core_count = int(total * rotation["core_ratio"])
    discovery_count = total - core_count

    # Get recent queries to avoid
    recent = get_recent_queries(conn, rotation["cooldown_days_before_reuse"])

    # Get keyword performance for weighting
    performance = get_keyword_performance(conn)

    # Build both sets (generate extra, then filter)
    core = build_core_queries(keywords, keywords["site_targets"], core_count * 3)
    discovery = build_discovery_queries(
        keywords, keywords["site_targets"], discovery_count * 3, performance
    )

    # Filter out recent queries
    core = [q for q in core if q["query"] not in recent]
    discovery = [q for q in discovery if q["query"] not in recent]

    # Select final set
    final_queries = core[:core_count] + discovery[:discovery_count]

    # Ensure we hit target count (backfill if needed)
    if len(final_queries) < total:
        remaining = [q for q in (core + discovery) if q not in final_queries]
        final_queries.extend(remaining[:total - len(final_queries)])

    final_queries = final_queries[:total]

    core_actual = sum(1 for q in final_queries if q["type"] == "core")
    disc_actual = sum(1 for q in final_queries if q["type"] == "discovery")

    print(f"Generated {len(final_queries)} queries: "
          f"{core_actual} core, {disc_actual} discovery")

    return final_queries


if __name__ == "__main__":
    from database import get_db, init_db
    init_db()
    conn = get_db()
    queries = generate_run_queries(conn)
    for q in queries:
        domains = q.get('include_domains') or ['(open web)']
        print(f"[{q['type']:>9}] {q['query']:<50} -> {domains}")
    conn.close()
