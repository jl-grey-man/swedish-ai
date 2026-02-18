"""Test configuration and fixtures."""
import sys
from pathlib import Path

# Add phases to path
sys.path.insert(0, str(Path(__file__).parent.parent / "phases"))

import pytest


@pytest.fixture
def test_db():
    """Create test database in memory."""
    # Import here to avoid circular dependency
    from database import init_db
    import sqlite3
    
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    
    yield conn
    
    conn.close()


@pytest.fixture
def sample_signal():
    """Sample signal for testing."""
    return {
        "signal_type": "social_post",
        "person": {
            "name": "Anna Andersson",
            "title": "HR Officer",
            "company": "Test AB"
        },
        "company": {
            "name": "Test AB",
            "industry": "Technology",
            "employee_count": "50"
        },
        "content": {
            "original_quote": "Vi spenderar 3 timmar varje dag med att kopiera data mellan system",
            "topic_tags": ["data entry", "manual process"],
            "expressed_problem": "Manual data copying between systems takes 3 hours daily",
            "expressed_need": "Automation of data transfer",
            "ai_awareness": "unaware"
        }
    }
