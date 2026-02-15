"""
Feedback Tool — Mark brief items as 'more like this' or 'less like this'.

Usage:
    python feedback.py more 42 "great lead, exactly this type of company"
    python feedback.py less 17 "too large, enterprise level"
    python feedback.py list          # Show recent feedback
    python feedback.py stats         # Show feedback summary
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "phases"))
from database import get_db, init_db


def add_feedback(rating: str, signal_id: int, note: str = ""):
    conn = get_db()
    conn.execute("""
        INSERT INTO feedback (signal_id, rating, note)
        VALUES (?, ?, ?)
    """, (signal_id, rating, note))
    conn.commit()
    
    # Show what was rated
    row = conn.execute("""
        SELECT es.company_name, es.person_name, es.expressed_problem
        FROM extracted_signals es WHERE es.id = ?
    """, (signal_id,)).fetchone()
    
    if row:
        print(f"✓ Marked signal #{signal_id} as [{rating.upper()}]")
        print(f"  Company: {row['company_name'] or 'unknown'}")
        print(f"  Problem: {row['expressed_problem'] or 'unknown'}")
        if note:
            print(f"  Note: {note}")
    else:
        print(f"✓ Marked signal #{signal_id} as [{rating.upper()}] (signal not found in DB)")
    
    conn.close()


def list_feedback():
    conn = get_db()
    rows = conn.execute("""
        SELECT f.rating, f.signal_id, f.note, f.created_at,
               es.company_name, es.expressed_problem
        FROM feedback f
        LEFT JOIN extracted_signals es ON es.id = f.signal_id
        ORDER BY f.created_at DESC
        LIMIT 20
    """).fetchall()
    
    if not rows:
        print("No feedback yet.")
        return
    
    for row in rows:
        icon = "👍" if row["rating"] == "more" else "👎"
        print(f"{icon} [{row['created_at'][:10]}] Signal #{row['signal_id']} "
              f"— {row['company_name'] or '?'} — {row['expressed_problem'] or '?'}")
        if row["note"]:
            print(f"   Note: {row['note']}")
    
    conn.close()


def show_stats():
    conn = get_db()
    
    more = conn.execute("SELECT COUNT(*) FROM feedback WHERE rating='more'").fetchone()[0]
    less = conn.execute("SELECT COUNT(*) FROM feedback WHERE rating='less'").fetchone()[0]
    
    print(f"Total feedback: {more + less}")
    print(f"  👍 More like this: {more}")
    print(f"  👎 Less like this: {less}")
    
    # Top rated topics
    if more > 0:
        rows = conn.execute("""
            SELECT es.topic_tags, COUNT(*) as cnt
            FROM feedback f
            JOIN extracted_signals es ON es.id = f.signal_id
            WHERE f.rating = 'more' AND es.topic_tags IS NOT NULL
            GROUP BY es.topic_tags
            ORDER BY cnt DESC
            LIMIT 5
        """).fetchall()
        
        if rows:
            print("\nMost liked topics:")
            for row in rows:
                tags = json.loads(row["topic_tags"])
                print(f"  {', '.join(tags)} ({row['cnt']}x)")
    
    conn.close()


if __name__ == "__main__":
    init_db()
    
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd in ("more", "less"):
        if len(sys.argv) < 3:
            print(f"Usage: python feedback.py {cmd} <signal_id> [note]")
            sys.exit(1)
        signal_id = int(sys.argv[2])
        note = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        add_feedback(cmd, signal_id, note)
    
    elif cmd == "list":
        list_feedback()
    
    elif cmd == "stats":
        show_stats()
    
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
