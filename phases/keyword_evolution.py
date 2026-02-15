"""
Keyword Evolution — The learning loop.

After each analysis run, this module:
1. Collects the actual language used in verified signals
2. Asks the LLM to suggest new discovery keywords
3. Retires underperforming keywords
4. Updates keywords.json for the next crawl

This is what makes the 34% exploration smart instead of random.
"""

import json
import os
from datetime import datetime
from pathlib import Path

from database import get_db

CONFIG_DIR = Path(__file__).parent.parent / "config"
KEYWORDS_PATH = CONFIG_DIR / "keywords.json"

# System prompt for keyword suggestion
KEYWORD_AGENT_PROMPT = """You are a keyword research agent for a system that 
monitors Swedish small businesses (SMBs) to find their problems and unmet needs.

You receive two inputs:
1. VERIFIED SIGNALS: Real quotes and posts from Swedish business owners, 
   employees, and job listings. These are verified — they actually exist.
2. CURRENT KEYWORDS: The keywords currently used to find these signals.

YOUR JOB: Suggest NEW search keywords based on the language real people used.

RULES:
- Only suggest Swedish-language keywords (or English terms commonly used in 
  Swedish business contexts)
- Focus on PAIN LANGUAGE — how do real people describe frustration, 
  bottlenecks, wasted time?
- Include informal/colloquial terms you see in the signals
- Include specific tool names, process names, or jargon from the signals
- Suggest terms that are ADJACENT to what was found — not identical
- Do NOT suggest keywords already in the current list
- Each keyword should be 1-4 words
- Suggest between 5 and 15 new keywords per run

OUTPUT FORMAT (JSON only, no other text):
{
  "new_keywords": [
    {
      "keyword": "the suggested term",
      "reason": "why this might surface useful signals",
      "derived_from": "which signal or quote inspired this"
    }
  ],
  "retire_candidates": [
    {
      "keyword": "underperforming keyword",
      "reason": "why it should be retired"
    }
  ]
}
"""


def get_recent_signals(conn, limit=100):
    """Get recent verified signals with their quotes."""
    rows = conn.execute("""
        SELECT es.original_quote, es.expressed_problem, es.expressed_need,
               es.topic_tags, es.company_name, es.person_title,
               rc.query_used, rc.keyword_type
        FROM extracted_signals es
        JOIN verified_signals vs ON vs.signal_id = es.id
        JOIN raw_crawl rc ON rc.source_hash = es.source_hash
        WHERE vs.final_status = 'verified'
        ORDER BY es.created_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    
    return [dict(row) for row in rows]


def get_keyword_performance(conn):
    """Get performance stats for all keywords."""
    rows = conn.execute("""
        SELECT keyword, keyword_type, times_used, times_produced_signal,
               hit_rate, active
        FROM keyword_history
        WHERE active = 1
    """).fetchall()
    return [dict(row) for row in rows]


def build_keyword_suggestion_prompt(signals, current_keywords, performance):
    """Build the prompt for the keyword suggestion LLM."""
    
    # Format signals
    signal_text = ""
    for s in signals[:50]:  # Cap to manage token count
        quote = s.get("original_quote", "")
        problem = s.get("expressed_problem", "")
        need = s.get("expressed_need", "")
        if quote:
            signal_text += f'- Quote: "{quote[:200]}"\n'
        if problem:
            signal_text += f'  Problem: {problem}\n'
        if need:
            signal_text += f'  Need: {need}\n'
        signal_text += "\n"
    
    # Format current keywords
    core = current_keywords.get("core_keywords", {})
    discovery = current_keywords.get("discovery_keywords", {})
    
    all_current = []
    for category in core.values():
        if isinstance(category, list):
            all_current.extend(category)
    for category in discovery.values():
        if isinstance(category, list):
            all_current.extend(category)
    
    # Format performance
    perf_text = ""
    underperformers = []
    for p in performance:
        if p["times_used"] >= 5 and p["hit_rate"] < 0.05:
            underperformers.append(p["keyword"])
            perf_text += f'- "{p["keyword"]}": used {p["times_used"]}x, '
            perf_text += f'hit rate {p["hit_rate"]:.1%} — UNDERPERFORMING\n'
        elif p["hit_rate"] > 0.2:
            perf_text += f'- "{p["keyword"]}": used {p["times_used"]}x, '
            perf_text += f'hit rate {p["hit_rate"]:.1%} — HIGH PERFORMER\n'
    
    user_prompt = f"""
VERIFIED SIGNALS FROM RECENT CRAWLS:
{signal_text}

CURRENT KEYWORDS (do not repeat these):
{json.dumps(all_current, ensure_ascii=False, indent=2)}

KEYWORD PERFORMANCE:
{perf_text if perf_text else "No performance data yet (first run)."}

Based on the actual language used in these signals, suggest new discovery 
keywords that might surface similar or adjacent business pain points.
"""
    
    return user_prompt


def update_keywords_file(new_keywords: list, retire: list):
    """
    Update keywords.json with new discovery keywords and retire old ones.
    Keeps a backup before modifying.
    """
    # Backup
    backup_path = KEYWORDS_PATH.with_suffix(
        f'.backup_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
    )
    
    with open(KEYWORDS_PATH, "r") as f:
        keywords = json.load(f)
    
    # Save backup
    with open(backup_path, "w") as f:
        json.dump(keywords, f, ensure_ascii=False, indent=2)
    
    # Add new discovery keywords
    from_signals = keywords["discovery_keywords"].get("from_signals", [])
    for kw in new_keywords:
        term = kw["keyword"]
        if term not in from_signals:
            from_signals.append(term)
    keywords["discovery_keywords"]["from_signals"] = from_signals
    
    # Retire underperformers from adjacent_terms
    retire_terms = {r["keyword"] for r in retire}
    adjacent = keywords["discovery_keywords"].get("adjacent_terms", [])
    adjacent = [t for t in adjacent if t not in retire_terms]
    keywords["discovery_keywords"]["adjacent_terms"] = adjacent
    
    # Also remove retired from from_signals
    from_signals = [t for t in from_signals if t not in retire_terms]
    keywords["discovery_keywords"]["from_signals"] = from_signals
    
    # Save updated
    with open(KEYWORDS_PATH, "w") as f:
        json.dump(keywords, f, ensure_ascii=False, indent=2)
    
    return {
        "added": len(new_keywords),
        "retired": len(retire),
        "total_discovery": len(from_signals) + len(adjacent),
        "backup": str(backup_path),
    }


def track_keyword_in_db(conn, keyword: str, keyword_type: str, source: str):
    """Add a keyword to the tracking table."""
    existing = conn.execute(
        "SELECT id FROM keyword_history WHERE keyword = ?", (keyword,)
    ).fetchone()
    
    if not existing:
        conn.execute("""
            INSERT INTO keyword_history (keyword, keyword_type, source)
            VALUES (?, ?, ?)
        """, (keyword, keyword_type, source))
        conn.commit()


def update_keyword_stats(conn, query_text: str, keyword_type: str, 
                         produced_signal: bool):
    """Update hit rate for keywords used in a query."""
    # Extract keywords from query (rough — between quotes)
    import re
    keywords_in_query = re.findall(r'"([^"]+)"', query_text)
    
    for kw in keywords_in_query:
        conn.execute("""
            UPDATE keyword_history 
            SET times_used = times_used + 1,
                times_produced_signal = times_produced_signal + ?,
                hit_rate = CAST(times_produced_signal + ? AS REAL) / 
                          (times_used + 1)
            WHERE keyword = ?
        """, (1 if produced_signal else 0, 
              1 if produced_signal else 0, kw))
    conn.commit()


# --- The actual call happens in the pipeline runner ---
# This module provides the prompt and the update logic.
# The LLM call is made by the pipeline to keep API key handling centralized.

KEYWORD_SYSTEM_PROMPT = KEYWORD_AGENT_PROMPT  # Exported for pipeline use
