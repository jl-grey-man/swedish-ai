#!/usr/bin/env python3
"""
Keyword Review CLI - Approve or reject LLM-suggested keywords

Usage:
    python scripts/review_keywords.py list              # Show pending suggestions
    python scripts/review_keywords.py approve 42        # Approve suggestion ID 42
    python scripts/review_keywords.py reject 43 "reason" # Reject with reason
    python scripts/review_keywords.py approve-top 5     # Auto-approve top 5 by confidence
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "smb.db"
KEYWORDS_PATH = Path(__file__).parent.parent / "config" / "keywords.json"


def get_db():
    """Connect to database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def list_suggestions(status="pending"):
    """List suggested keywords."""
    conn = get_db()
    
    rows = conn.execute("""
        SELECT id, query_text, suggested_by, reasoning,
               hit_rate_estimate, suggested_at,
               source_signals
        FROM suggested_queries
        WHERE status = ?
        ORDER BY hit_rate_estimate DESC, suggested_at DESC
    """, (status,)).fetchall()
    
    if not rows:
        print(f"No {status} suggestions found.")
        return
    
    print(f"\n{'ID':<6} {'Keyword':<30} {'Source':<20} {'Est. Hit Rate':<12} {'Signals'}")
    print("-" * 90)
    
    for row in rows:
        signal_count = len(json.loads(row["source_signals"] or "[]"))
        hit_rate = row["hit_rate_estimate"] or 0.0
        print(f"{row['id']:<6} {row['query_text']:<30} {row['suggested_by']:<20} {hit_rate:>6.1%}      {signal_count} signals")
    
    print(f"\nTotal: {len(rows)} {status} suggestions")
    conn.close()


def show_detail(suggestion_id):
    """Show detailed info about a suggestion."""
    conn = get_db()
    
    row = conn.execute("""
        SELECT * FROM suggested_queries WHERE id = ?
    """, (suggestion_id,)).fetchone()
    
    if not row:
        print(f"Suggestion {suggestion_id} not found.")
        conn.close()
        return
    
    print(f"\nSuggestion #{row['id']}")
    print(f"Keyword: {row['query_text']}")
    print(f"Suggested by: {row['suggested_by']}")
    print(f"Reasoning: {row['reasoning']}")
    print(f"Est. hit rate: {row['hit_rate_estimate'] or 0.0:.1%}")
    print(f"Source signals: {row['source_signals']}")
    print(f"Status: {row['status']}")
    print(f"Suggested at: {row['suggested_at']}")
    
    conn.close()


def approve_suggestion(suggestion_id):
    """Approve a suggestion and add to keywords.json."""
    conn = get_db()
    
    # Get suggestion
    row = conn.execute("""
        SELECT query_text, suggested_by FROM suggested_queries WHERE id = ?
    """, (suggestion_id,)).fetchone()
    
    if not row:
        print(f"Suggestion {suggestion_id} not found.")
        conn.close()
        return
    
    keyword = row["query_text"]
    
    # Load keywords.json
    with open(KEYWORDS_PATH, 'r') as f:
        config = json.load(f)
    
    # Add to appropriate section
    if row["suggested_by"] == "keyword_evolution":
        target = config["discovery_keywords"]["from_signals"]
    else:
        target = config["discovery_keywords"]["adjacent_terms"]
    
    if keyword not in target:
        target.append(keyword)
        
        # Save keywords.json
        with open(KEYWORDS_PATH, 'w') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # Mark as approved
        conn.execute("""
            UPDATE suggested_queries
            SET status = 'approved',
                reviewed_at = datetime('now'),
                reviewed_by = 'manual_review'
            WHERE id = ?
        """, (suggestion_id,))
        conn.commit()
        
        print(f"✓ Approved and added: {keyword}")
    else:
        print(f"Keyword already exists: {keyword}")
        # Mark as obsolete
        conn.execute("""
            UPDATE suggested_queries
            SET status = 'obsolete',
                review_note = 'Already in keywords.json'
            WHERE id = ?
        """, (suggestion_id,))
        conn.commit()
    
    conn.close()


def reject_suggestion(suggestion_id, reason=""):
    """Reject a suggestion."""
    conn = get_db()
    
    conn.execute("""
        UPDATE suggested_queries
        SET status = 'rejected',
            reviewed_at = datetime('now'),
            reviewed_by = 'manual_review',
            review_note = ?
        WHERE id = ?
    """, (reason, suggestion_id))
    conn.commit()
    
    print(f"✓ Rejected suggestion {suggestion_id}")
    if reason:
        print(f"  Reason: {reason}")
    
    conn.close()


def approve_top_n(n):
    """Auto-approve top N suggestions by confidence."""
    conn = get_db()
    
    rows = conn.execute("""
        SELECT id, query_text FROM suggested_queries
        WHERE status = 'pending'
        ORDER BY hit_rate_estimate DESC
        LIMIT ?
    """, (n,)).fetchall()
    
    if not rows:
        print("No pending suggestions to approve.")
        conn.close()
        return
    
    print(f"Approving top {len(rows)} suggestions:")
    for row in rows:
        print(f"  - {row['query_text']}")
        approve_suggestion(row['id'])
    
    print(f"\n✓ Approved {len(rows)} keywords")
    conn.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        status = sys.argv[2] if len(sys.argv) > 2 else "pending"
        list_suggestions(status)
    
    elif command == "detail":
        if len(sys.argv) < 3:
            print("Usage: review_keywords.py detail <id>")
            sys.exit(1)
        show_detail(int(sys.argv[2]))
    
    elif command == "approve":
        if len(sys.argv) < 3:
            print("Usage: review_keywords.py approve <id>")
            sys.exit(1)
        approve_suggestion(int(sys.argv[2]))
    
    elif command == "reject":
        if len(sys.argv) < 3:
            print("Usage: review_keywords.py reject <id> [\"reason\"]")
            sys.exit(1)
        reason = sys.argv[3] if len(sys.argv) > 3 else ""
        reject_suggestion(int(sys.argv[2]), reason)
    
    elif command == "approve-top":
        if len(sys.argv) < 3:
            print("Usage: review_keywords.py approve-top <n>")
            sys.exit(1)
        approve_top_n(int(sys.argv[2]))
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
