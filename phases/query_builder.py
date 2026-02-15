"""
Query Builder — Generates search queries with 66/34 core/discovery split.
Handles rotation, deduplication, and keyword combination logic.
"""

import json
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from itertools import product as iter_product

CONFIG_DIR = Path(__file__).parent.parent / "config"


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
    Build the 66% — structured queries from known pain terms.
    Combines: site + pain_signal + context, or site + task + pain.
    """
    queries = []
    
    pain = keywords["core_keywords"]["pain_signals"]
    ai = keywords["core_keywords"]["ai_awareness"]
    biz = keywords["core_keywords"]["business_context"]
    tasks = keywords["core_keywords"]["specific_tasks"]
    sites = keywords["site_targets"]
    
    # Pattern 1: site + pain + business context
    for site_key, site_val in sites.items():
        for p in pain:
            for b in random.sample(biz, min(2, len(biz))):
                queries.append({
                    "query": f'{site_val} "{p}" "{b}"',
                    "type": "core",
                    "site": site_key,
                    "keywords_used": [p, b]
                })
    
    # Pattern 2: site + specific task + pain
    for site_key, site_val in sites.items():
        for t in tasks:
            for p in random.sample(pain, min(2, len(pain))):
                queries.append({
                    "query": f'{site_val} "{t}" "{p}"',
                    "type": "core",
                    "site": site_key,
                    "keywords_used": [t, p]
                })
    
    # Pattern 3: site + AI term + business + pain (more specific)
    for site_key, site_val in sites.items():
        for a in ai:
            for b in random.sample(biz, min(2, len(biz))):
                queries.append({
                    "query": f'{site_val} "{a}" "{b}"',
                    "type": "core",
                    "site": site_key,
                    "keywords_used": [a, b]
                })

    # Shuffle and limit
    random.shuffle(queries)
    return queries[:count]


def build_discovery_queries(keywords, site_targets, count, performance=None):
    """
    Build the 34% — exploratory queries from LLM-suggested and adjacent terms.
    Weighted by past performance if available.
    """
    queries = []
    
    discovery = keywords["discovery_keywords"]
    from_signals = discovery.get("from_signals", [])
    adjacent = discovery.get("adjacent_terms", [])
    biz = keywords["core_keywords"]["business_context"]
    sites = keywords["site_targets"]
    
    all_discovery = from_signals + adjacent
    if not all_discovery:
        return []
    
    # Weight by performance if we have data
    if performance:
        weighted = []
        for kw in all_discovery:
            perf = performance.get(kw, {})
            # New keywords get a boost, proven ones get weight, 
            # zero-hit ones get deprioritized
            if perf.get("times_used", 0) == 0:
                weight = 1.5  # New keyword boost
            elif perf.get("hit_rate", 0) > 0:
                weight = 1.0 + perf["hit_rate"]
            else:
                weight = 0.3  # Used but never hit
            weighted.extend([kw] * max(1, int(weight * 3)))
        all_discovery = weighted
    
    # Build queries — more freeform than core
    for site_key, site_val in sites.items():
        for _ in range(3):  # 3 attempts per site
            kw = random.choice(all_discovery)
            # Sometimes pair with business context, sometimes alone
            if random.random() > 0.4:
                b = random.choice(biz)
                queries.append({
                    "query": f'{site_val} "{kw}" "{b}"',
                    "type": "discovery",
                    "site": site_key,
                    "keywords_used": [kw, b]
                })
            else:
                queries.append({
                    "query": f'{site_val} "{kw}"',
                    "type": "discovery",
                    "site": site_key,
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
    max_per_site = rotation["max_per_site"]
    
    # Get recent queries to avoid
    recent = get_recent_queries(conn, rotation["cooldown_days_before_reuse"])
    
    # Get keyword performance for weighting
    performance = get_keyword_performance(conn)
    
    # Build both sets
    core = build_core_queries(keywords, keywords["site_targets"], core_count * 3)
    discovery = build_discovery_queries(
        keywords, keywords["site_targets"], discovery_count * 3, performance
    )
    
    # Filter out recent queries
    core = [q for q in core if q["query"] not in recent]
    discovery = [q for q in discovery if q["query"] not in recent]
    
    # Enforce per-site limits
    site_counts = {}
    final_queries = []
    
    for q in (core[:core_count] + discovery[:discovery_count]):
        site = q["site"]
        site_counts[site] = site_counts.get(site, 0) + 1
        if site_counts[site] <= max_per_site:
            final_queries.append(q)
    
    # Ensure we hit target count
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
    for q in queries[:10]:
        print(f"[{q['type']:>9}] {q['query']}")
    print(f"... and {len(queries) - 10} more")
    conn.close()
