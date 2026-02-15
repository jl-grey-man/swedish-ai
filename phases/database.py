"""
Database schema and helpers for the SMB Intelligence System.
All crawled data, signals, and analysis stored in SQLite.
"""

import sqlite3
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "intel.db"


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""

    -- Raw crawl results. Never modified after insertion.
    CREATE TABLE IF NOT EXISTS raw_crawl (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_hash TEXT UNIQUE NOT NULL,
        source_url TEXT NOT NULL,
        source_domain TEXT NOT NULL,
        crawl_timestamp TEXT NOT NULL,
        content_date TEXT,
        page_title TEXT,
        raw_text TEXT NOT NULL,
        raw_html TEXT,
        query_used TEXT,
        keyword_type TEXT CHECK(keyword_type IN ('core', 'discovery')),
        http_status INTEGER,
        created_at TEXT DEFAULT (datetime('now'))
    );

    -- Extracted signals from LLM Agent 1
    CREATE TABLE IF NOT EXISTS extracted_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_hash TEXT NOT NULL,
        signal_type TEXT CHECK(signal_type IN (
            'job_posting', 'social_post', 'news_mention',
            'forum_post', 'company_data'
        )),
        person_name TEXT,
        person_title TEXT,
        person_company TEXT,
        company_name TEXT,
        company_org_number TEXT,
        company_industry TEXT,
        company_employee_count TEXT,
        original_quote TEXT,
        expressed_problem TEXT,
        expressed_need TEXT,
        ai_awareness TEXT CHECK(ai_awareness IN (
            'using_ai', 'exploring_ai', 'skeptical',
            'unaware', NULL
        )),
        topic_tags TEXT,  -- JSON array
        extraction_model TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (source_hash) REFERENCES raw_crawl(source_hash)
    );

    -- Verification results
    CREATE TABLE IF NOT EXISTS verified_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_id INTEGER NOT NULL,
        quote_check TEXT CHECK(quote_check IN ('passed', 'failed', 'partial')),
        quote_similarity REAL,
        url_check TEXT CHECK(url_check IN ('live', 'dead', 'redirect', 'timeout')),
        company_verified INTEGER DEFAULT 0,
        company_allabolag_data TEXT,  -- JSON from Allabolag
        is_duplicate INTEGER DEFAULT 0,
        duplicate_of INTEGER,
        final_status TEXT CHECK(final_status IN ('verified', 'rejected', 'weak')),
        verified_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (signal_id) REFERENCES extracted_signals(id)
    );

    -- Analysis results per run
    CREATE TABLE IF NOT EXISTS analysis_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_date TEXT NOT NULL,
        focus_file_hash TEXT,
        signals_processed INTEGER,
        signals_verified INTEGER,
        problem_clusters TEXT,  -- JSON
        white_spaces TEXT,      -- JSON
        watchlist TEXT,          -- JSON
        sector_patterns TEXT,   -- JSON
        discovery_suggestions TEXT,  -- JSON
        keyword_suggestions TEXT,    -- JSON (new keywords from signals)
        created_at TEXT DEFAULT (datetime('now'))
    );

    -- User feedback on brief items
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_id INTEGER,
        analysis_run_id INTEGER,
        rating TEXT CHECK(rating IN ('more', 'less')),
        note TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    -- Discovered sources (the 34% exploration)
    CREATE TABLE IF NOT EXISTS discovered_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL,
        source_type TEXT,
        discovered_from_signal INTEGER,
        hit_count INTEGER DEFAULT 0,
        promoted_to_fixed INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    );

    -- Query log to track what was searched and avoid repeats
    CREATE TABLE IF NOT EXISTS query_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query_text TEXT NOT NULL,
        keyword_type TEXT CHECK(keyword_type IN ('core', 'discovery')),
        site_target TEXT,
        results_count INTEGER,
        useful_results INTEGER DEFAULT 0,
        run_date TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    );

    -- Keyword evolution tracking
    CREATE TABLE IF NOT EXISTS keyword_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT NOT NULL,
        keyword_type TEXT CHECK(keyword_type IN ('core', 'discovery')),
        source TEXT,  -- 'initial', 'llm_suggested', 'promoted_from_discovery'
        times_used INTEGER DEFAULT 0,
        times_produced_signal INTEGER DEFAULT 0,
        hit_rate REAL DEFAULT 0.0,
        active INTEGER DEFAULT 1,
        added_date TEXT DEFAULT (datetime('now')),
        retired_date TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_crawl_hash ON raw_crawl(source_hash);
    CREATE INDEX IF NOT EXISTS idx_crawl_domain ON raw_crawl(source_domain);
    CREATE INDEX IF NOT EXISTS idx_crawl_date ON raw_crawl(crawl_timestamp);
    CREATE INDEX IF NOT EXISTS idx_signals_company ON extracted_signals(company_name);
    CREATE INDEX IF NOT EXISTS idx_signals_source ON extracted_signals(source_hash);
    CREATE INDEX IF NOT EXISTS idx_verified_status ON verified_signals(final_status);
    CREATE INDEX IF NOT EXISTS idx_query_date ON query_log(run_date);

    """)
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


def make_source_hash(url: str, content: str) -> str:
    """Create unique hash for a crawled page."""
    raw = f"{url}|{content[:500]}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def store_crawl_result(conn, url: str, domain: str, title: str,
                       raw_text: str, raw_html: str, query: str,
                       keyword_type: str, http_status: int,
                       content_date: str = None) -> str:
    """Store a raw crawl result. Returns source_hash."""
    source_hash = make_source_hash(url, raw_text)
    try:
        conn.execute("""
            INSERT INTO raw_crawl 
            (source_hash, source_url, source_domain, crawl_timestamp,
             content_date, page_title, raw_text, raw_html, query_used,
             keyword_type, http_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            source_hash, url, domain, 
            datetime.now(timezone.utc).isoformat(),
            content_date, title, raw_text, raw_html, query,
            keyword_type, http_status
        ))
        conn.commit()
        return source_hash
    except sqlite3.IntegrityError:
        # Duplicate — already crawled
        return None


def log_query(conn, query: str, keyword_type: str, 
              site_target: str, results_count: int):
    """Log a search query for rotation tracking."""
    conn.execute("""
        INSERT INTO query_log (query_text, keyword_type, site_target,
                              results_count, run_date)
        VALUES (?, ?, ?, ?, ?)
    """, (query, keyword_type, site_target, results_count,
          datetime.now(timezone.utc).strftime('%Y-%m-%d')))
    conn.commit()


if __name__ == "__main__":
    init_db()
