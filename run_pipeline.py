"""
Pipeline Runner — Orchestrates all phases in sequence.

Usage:
    python run_pipeline.py              # Full run (all phases)
    python run_pipeline.py --crawl-only # Just Phase 1
    python run_pipeline.py --skip-crawl # Phases 2-6 on existing data
    python run_pipeline.py --brief-only # Regenerate brief from last analysis

Requires ANTHROPIC_API_KEY environment variable for LLM phases.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add phases directory to path
sys.path.insert(0, str(Path(__file__).parent / "phases"))

from database import get_db, init_db
from phase1_crawl import run_crawl
from phase2_extract import (
    EXTRACT_SYSTEM_PROMPT, build_extraction_prompt,
    parse_extraction_response, store_extracted_signals
)
from phase3_verify import run_verification
from phase4_5_analyze_brief import (
    ANALYZE_SYSTEM_PROMPT, build_analysis_prompt,
    BRIEF_SYSTEM_PROMPT, build_brief_prompt
)
from keyword_evolution import (
    KEYWORD_SYSTEM_PROMPT, get_recent_signals, get_keyword_performance,
    build_keyword_suggestion_prompt, update_keywords_file,
    track_keyword_in_db, update_keyword_stats
)

# ---- Config ----
PROJECT_DIR = Path(__file__).parent
CONFIG_DIR = PROJECT_DIR / "config"
BRIEFS_DIR = PROJECT_DIR / "briefs"
DATA_DIR = PROJECT_DIR / "data"
LOG_DIR = DATA_DIR / "logs"

BRIEFS_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

LLM_MODEL = "claude-sonnet-4-20250514"  # Good balance of cost/quality
LLM_MAX_TOKENS = 4096

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "pipeline.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("pipeline")


# ---- LLM Client ----
def call_llm(system_prompt: str, user_prompt: str, 
             max_tokens: int = LLM_MAX_TOKENS) -> str:
    """Call Anthropic API. Returns response text."""
    try:
        import anthropic
    except ImportError:
        log.error("anthropic package not installed. Run: "
                  "pip install anthropic --break-system-packages")
        sys.exit(1)
    
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY not set. Export it before running.")
        sys.exit(1)
    
    client = anthropic.Anthropic(api_key=api_key)
    
    try:
        response = client.messages.create(
            model=LLM_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return response.content[0].text
    except Exception as e:
        log.error(f"LLM call failed: {e}")
        return ""


def load_focus():
    """Load the focus file."""
    focus_path = CONFIG_DIR / "focus.txt"
    if focus_path.exists():
        return focus_path.read_text()
    return "No focus file configured."


def load_feedback(conn):
    """Load recent feedback."""
    rows = conn.execute("""
        SELECT signal_id, rating, note 
        FROM feedback 
        WHERE created_at >= datetime('now', '-7 days')
    """).fetchall()
    return [dict(row) for row in rows]


def load_previous_analysis(conn):
    """Load the most recent analysis run."""
    row = conn.execute("""
        SELECT problem_clusters, white_spaces, watchlist, sector_patterns
        FROM analysis_runs
        ORDER BY created_at DESC LIMIT 1
    """).fetchone()
    
    if not row:
        return None
    
    return {
        "problem_clusters": json.loads(row["problem_clusters"] or "[]"),
        "white_spaces": json.loads(row["white_spaces"] or "[]"),
        "watchlist": json.loads(row["watchlist"] or "[]"),
        "sector_patterns": json.loads(row["sector_patterns"] or "[]"),
    }


# ---- Phase Runners ----

def run_phase1():
    """Phase 1: Crawl."""
    log.info("=" * 60)
    log.info("PHASE 1: CRAWL")
    log.info("=" * 60)
    return run_crawl()


def run_phase2(conn):
    """Phase 2: Extract signals from raw crawl data."""
    log.info("=" * 60)
    log.info("PHASE 2: EXTRACT")
    log.info("=" * 60)
    
    # Get unprocessed crawl results
    rows = conn.execute("""
        SELECT rc.source_hash, rc.source_url, rc.page_title, 
               rc.raw_text, rc.query_used
        FROM raw_crawl rc
        LEFT JOIN extracted_signals es ON es.source_hash = rc.source_hash
        WHERE es.id IS NULL
        AND length(rc.raw_text) > 100
        ORDER BY rc.created_at DESC
    """).fetchall()
    
    log.info(f"Processing {len(rows)} unextracted pages")
    
    total_signals = 0
    
    for i, row in enumerate(rows):
        log.info(f"  [{i+1}/{len(rows)}] Extracting from {row['source_url'][:70]}")
        
        # Build prompt
        user_prompt = build_extraction_prompt(
            source_hash=row["source_hash"],
            url=row["source_url"],
            title=row["page_title"],
            raw_text=row["raw_text"],
            query_used=row["query_used"]
        )
        
        # Call LLM
        response = call_llm(EXTRACT_SYSTEM_PROMPT, user_prompt, max_tokens=2048)
        
        if not response:
            continue
        
        # Parse and store
        signals = parse_extraction_response(response, row["source_hash"])
        if signals:
            stored = store_extracted_signals(conn, signals, LLM_MODEL)
            total_signals += stored
            log.info(f"    Extracted {stored} signals")
    
    log.info(f"Phase 2 complete: {total_signals} signals extracted")
    return total_signals


def run_phase3(conn):
    """Phase 3: Verify."""
    log.info("=" * 60)
    log.info("PHASE 3: VERIFY")
    log.info("=" * 60)
    return run_verification(conn)


def run_phase4(conn):
    """Phase 4: Analyze."""
    log.info("=" * 60)
    log.info("PHASE 4: ANALYZE")
    log.info("=" * 60)
    
    # Get verified signals
    rows = conn.execute("""
        SELECT es.id, es.person_name, es.person_title, es.person_company,
               es.company_name, es.company_industry, es.company_employee_count,
               es.original_quote, es.expressed_problem, es.expressed_need,
               es.ai_awareness, es.topic_tags, rc.source_url
        FROM extracted_signals es
        JOIN verified_signals vs ON vs.signal_id = es.id
        JOIN raw_crawl rc ON rc.source_hash = es.source_hash
        WHERE vs.final_status IN ('verified', 'weak')
        ORDER BY es.created_at DESC
        LIMIT 200
    """).fetchall()
    
    signals = [dict(row) for row in rows]
    log.info(f"Analyzing {len(signals)} verified signals")
    
    if not signals:
        log.warning("No verified signals to analyze.")
        return {}
    
    # Build prompt
    focus = load_focus()
    feedback = load_feedback(conn)
    previous = load_previous_analysis(conn)
    
    user_prompt = build_analysis_prompt(signals, focus, feedback, previous)
    
    # Call LLM
    response = call_llm(ANALYZE_SYSTEM_PROMPT, user_prompt, max_tokens=4096)
    
    if not response:
        return {}
    
    # Parse response
    try:
        # Clean potential markdown
        text = response.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        analysis = json.loads(text)
    except json.JSONDecodeError:
        log.error(f"Could not parse analysis response")
        analysis = {"error": "parse_failure", "raw": response[:500]}
    
    # Store analysis run
    import hashlib
    focus_hash = hashlib.md5(focus.encode()).hexdigest()[:8]
    
    conn.execute("""
        INSERT INTO analysis_runs
        (run_date, focus_file_hash, signals_processed, signals_verified,
         problem_clusters, white_spaces, watchlist, sector_patterns,
         discovery_suggestions)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        focus_hash,
        len(signals),
        len([s for s in signals]),
        json.dumps(analysis.get("problem_clusters", []), ensure_ascii=False),
        json.dumps(analysis.get("white_spaces", []), ensure_ascii=False),
        json.dumps(analysis.get("watchlist_companies", []), ensure_ascii=False),
        json.dumps(analysis.get("sector_patterns", []), ensure_ascii=False),
        json.dumps(analysis.get("discovery_suggestions", []), ensure_ascii=False),
    ))
    conn.commit()
    
    log.info(f"Analysis complete: {len(analysis.get('problem_clusters', []))} clusters, "
             f"{len(analysis.get('white_spaces', []))} white spaces")
    
    return analysis


def run_phase5(conn, analysis: dict):
    """Phase 5: Generate brief."""
    log.info("=" * 60)
    log.info("PHASE 5: BRIEF")
    log.info("=" * 60)
    
    # Get signals for citation
    rows = conn.execute("""
        SELECT es.id, es.person_name, es.person_title,
               es.company_name, es.original_quote, es.expressed_problem,
               rc.source_url
        FROM extracted_signals es
        JOIN verified_signals vs ON vs.signal_id = es.id
        JOIN raw_crawl rc ON rc.source_hash = es.source_hash
        WHERE vs.final_status = 'verified'
        ORDER BY es.created_at DESC
        LIMIT 100
    """).fetchall()
    
    signals = [dict(row) for row in rows]
    run_date = datetime.now().strftime('%Y-%m-%d')
    focus = load_focus()
    
    # First line of focus as summary
    focus_summary = focus.split('\n')[0] if focus else "No focus set"
    
    user_prompt = build_brief_prompt(analysis, signals, run_date, focus_summary)
    response = call_llm(BRIEF_SYSTEM_PROMPT, user_prompt, max_tokens=4096)
    
    if not response:
        log.error("Brief generation failed")
        return
    
    # Save brief
    brief_path = BRIEFS_DIR / f"brief_{run_date}.md"
    brief_path.write_text(response)
    
    log.info(f"Brief saved to {brief_path}")
    return str(brief_path)


def run_phase6_keywords(conn):
    """Phase 6: Evolve keywords based on what was found."""
    log.info("=" * 60)
    log.info("PHASE 6: KEYWORD EVOLUTION")
    log.info("=" * 60)
    
    signals = get_recent_signals(conn, limit=100)
    if not signals:
        log.info("No signals yet — skipping keyword evolution")
        return
    
    with open(CONFIG_DIR / "keywords.json", "r") as f:
        current_keywords = json.load(f)
    
    performance = get_keyword_performance(conn)
    
    user_prompt = build_keyword_suggestion_prompt(
        signals, current_keywords, performance
    )
    
    response = call_llm(KEYWORD_SYSTEM_PROMPT, user_prompt, max_tokens=2048)
    
    if not response:
        return
    
    try:
        text = response.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        suggestions = json.loads(text)
    except json.JSONDecodeError:
        log.error("Could not parse keyword suggestions")
        return
    
    new_kws = suggestions.get("new_keywords", [])
    retire = suggestions.get("retire_candidates", [])
    
    if new_kws:
        result = update_keywords_file(new_kws, retire)
        log.info(f"Keywords updated: +{result['added']} added, "
                 f"-{result['retired']} retired, "
                 f"{result['total_discovery']} total discovery keywords")
        
        # Track new keywords in DB
        for kw in new_kws:
            track_keyword_in_db(conn, kw["keyword"], "discovery", "llm_suggested")
    else:
        log.info("No new keywords suggested")


# ---- Main ----

def main():
    parser = argparse.ArgumentParser(description="SMB Intelligence Pipeline")
    parser.add_argument("--crawl-only", action="store_true",
                       help="Run only Phase 1 (crawl)")
    parser.add_argument("--skip-crawl", action="store_true",
                       help="Skip Phase 1, run Phases 2-6")
    parser.add_argument("--brief-only", action="store_true",
                       help="Regenerate brief from last analysis")
    args = parser.parse_args()
    
    log.info("=" * 60)
    log.info(f"SMB INTELLIGENCE PIPELINE — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info("=" * 60)
    
    init_db()
    conn = get_db()
    
    try:
        if args.brief_only:
            previous = load_previous_analysis(conn)
            if previous:
                run_phase5(conn, previous)
            else:
                log.error("No previous analysis found")
            return
        
        # Phase 1: Crawl
        if not args.skip_crawl:
            crawl_stats = run_phase1()
            log.info(f"Crawl stats: {json.dumps(crawl_stats)}")
        
        if args.crawl_only:
            return
        
        # Phase 2: Extract
        extract_count = run_phase2(conn)
        
        # Phase 3: Verify
        verify_stats = run_phase3(conn)
        
        # Phase 4: Analyze
        analysis = run_phase4(conn)
        
        # Phase 5: Brief
        if analysis and not analysis.get("error"):
            brief_path = run_phase5(conn, analysis)
            if brief_path:
                log.info(f"\n{'='*60}")
                log.info(f"TODAY'S BRIEF: {brief_path}")
                log.info(f"{'='*60}\n")
        
        # Phase 6: Keyword Evolution
        run_phase6_keywords(conn)
        
        # Summary
        log.info("\n" + "=" * 60)
        log.info("PIPELINE COMPLETE")
        log.info("=" * 60)
        
    finally:
        conn.close()


if __name__ == "__main__":
    main()
