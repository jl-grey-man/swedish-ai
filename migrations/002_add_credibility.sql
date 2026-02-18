-- Migration: Add credibility tracking
-- Run with: sqlite3 /mnt/storage/swedish-ai/smb.db < migrations/002_add_credibility.sql

-- Create credibility scores table
CREATE TABLE IF NOT EXISTS credibility_scores (
    id INTEGER PRIMARY KEY,
    signal_id INTEGER NOT NULL REFERENCES extracted_signals(id),
    sales_intent_score INTEGER CHECK(sales_intent_score BETWEEN 1 AND 10),
    objectivity_score INTEGER CHECK(objectivity_score BETWEEN 1 AND 10),
    sponsored_content BOOLEAN DEFAULT 0,
    detected_patterns TEXT,  -- JSON array of red flags
    reasoning TEXT,
    language TEXT,  -- sv, da, no, fi, is, en, other
    verdict TEXT NOT NULL CHECK(verdict IN ('accept', 'review', 'reject')),
    checked_at TEXT DEFAULT (datetime('now')),
    UNIQUE(signal_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_credibility_verdict ON credibility_scores(verdict);
CREATE INDEX IF NOT EXISTS idx_credibility_sponsored ON credibility_scores(sponsored_content);
CREATE INDEX IF NOT EXISTS idx_credibility_sales_score ON credibility_scores(sales_intent_score);

-- Create discovery suggestions table (for quality audit agent)
CREATE TABLE IF NOT EXISTS discovery_suggestions (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,  -- 'quality_audit', 'keyword_evolution', 'manual'
    query_text TEXT NOT NULL,
    reason TEXT,
    priority REAL DEFAULT 0.5,
    created_at TEXT DEFAULT (datetime('now')),
    used_at TEXT,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'used', 'retired'))
);

CREATE INDEX IF NOT EXISTS idx_discovery_status ON discovery_suggestions(status);
CREATE INDEX IF NOT EXISTS idx_discovery_priority ON discovery_suggestions(priority);

-- Record migration
INSERT INTO schema_version (version, description, applied_at)
VALUES (2, 'Add credibility_scores and discovery_suggestions tables', datetime('now'));
