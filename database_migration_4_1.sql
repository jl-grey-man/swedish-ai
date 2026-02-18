-- Migration 4.1: Suggested Queries Tracking
-- Purpose: Save LLM-suggested keywords for manual review instead of auto-adding

CREATE TABLE IF NOT EXISTS suggested_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    suggested_by TEXT NOT NULL,  -- 'keyword_evolution' or 'quality_audit'
    query_text TEXT NOT NULL,
    source_signals TEXT,  -- JSON array of signal IDs that led to suggestion
    reasoning TEXT,
    hit_rate_estimate REAL,  -- LLM's confidence this will be valuable
    suggested_at TEXT DEFAULT (datetime('now')),
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'obsolete')),
    reviewed_at TEXT,
    reviewed_by TEXT,  -- For future multi-user support
    review_note TEXT
);

CREATE INDEX IF NOT EXISTS idx_suggested_status ON suggested_queries(status);
CREATE INDEX IF NOT EXISTS idx_suggested_by ON suggested_queries(suggested_by);
CREATE INDEX IF NOT EXISTS idx_suggested_at ON suggested_queries(suggested_at);

-- Also track which suggestions got used and performed well
CREATE TABLE IF NOT EXISTS keyword_performance_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    suggestion_id INTEGER REFERENCES suggested_queries(id),
    run_date TEXT,
    queries_made INTEGER,
    signals_found INTEGER,
    verified_signals INTEGER,
    hit_rate REAL,
    UNIQUE(keyword, run_date)
);

CREATE INDEX IF NOT EXISTS idx_kw_perf_keyword ON keyword_performance_history(keyword);
CREATE INDEX IF NOT EXISTS idx_kw_perf_suggestion ON keyword_performance_history(suggestion_id);

-- Migration complete
-- To apply: sqlite3 /mnt/storage/swedish-ai/smb.db < database_migration_4_1.sql
