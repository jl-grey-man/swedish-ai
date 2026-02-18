# Quick Start for Claude Code

## Current State

**Repository**: `/home/pi/swedish-ai` (or wherever you cloned it)  
**Database**: `/mnt/storage/swedish-ai/smb.db` (SQLite)  
**Config**: `/home/pi/swedish-ai/config/`  
**Storage**: `/mnt/storage/swedish-ai/` (briefs, audits, research reports)

## System Architecture

6-phase pipeline that runs daily:

1. **CRAWL** (deterministic) - Google dorking, page fetching
2. **EXTRACT** (LLM) - Signal extraction from raw text
3. **VERIFY** (deterministic) - Quote matching, URL checking, company validation
4. **ANALYZE** (LLM) - Pattern recognition, clustering
5. **BRIEF** (LLM) - Report generation with citations
6. **KEYWORD EVOLUTION** (LLM) - Learning new search terms

## What Currently Works

✅ All 6 phases functional  
✅ SQLite database with proper schema  
✅ Keyword rotation (66/34 split)  
✅ Query cooldown (3-day reuse prevention)  
✅ Allabolag company enrichment  
✅ Feedback system (`python feedback.py more 42 "note"`)

## What's Being Added

See `docs/implementation/IMPLEMENTATION_PLAN.md` for atomic steps.

**Priority additions:**
1. Reduce query count to 20 (from 60)
2. JSON schema validation for all LLM calls
3. Credibility filter (block sponsored content)
4. 6-month recency filter
5. Quality audit agent

## Implementation Status Tracking

Check current progress:
```bash
cat IMPLEMENTATION_STATUS.json
```

Mark step complete:
```bash
./scripts/mark_step_complete.sh 1.1 "Reduced to 20 queries"
```

## Running the System

**Full pipeline:**
```bash
python run_pipeline.py
```

**Individual phases:**
```bash
python phases/phase1_crawl.py
python phases/phase2_extract.py
python phases/phase3_verify.py
python phases/phase4_analyze.py
python phases/phase5_brief.py
python phases/keyword_evolution.py
```

**Testing:**
```bash
pytest tests/ -v
```

**Feedback:**
```bash
python feedback.py more 123 "Great signal, exactly this type"
python feedback.py less 456 "Sales pitch, not a real problem"
python feedback.py list
python feedback.py stats
```

## File Structure

```
swedish-ai/
├── config/
│   ├── keywords.json          # Search terms (66/34 split)
│   ├── focus.txt              # Current business focus
│   └── geography.json         # Nordic market config (new)
├── phases/
│   ├── database.py            # SQLite schema
│   ├── phase1_crawl.py        # Scraping
│   ├── phase2_extract.py      # LLM extraction
│   ├── phase2_5_credibility.py # NEW: Sales pitch detection
│   ├── phase3_verify.py       # Verification
│   ├── phase4_5_analyze_brief.py
│   ├── keyword_evolution.py
│   ├── llm_utils.py          # NEW: JSON schema enforcement
│   └── query_builder.py
├── docs/
│   ├── QUICK_START.md         # This file
│   ├── implementation/
│   │   └── IMPLEMENTATION_PLAN.md
│   ├── schemas/
│   │   └── ALL_SCHEMAS.json
│   └── prompts/
│       └── ALL_PROMPTS.md
├── tests/                     # Pytest test suite
├── run_pipeline.py            # Main orchestrator
├── feedback.py                # User feedback tool
└── IMPLEMENTATION_STATUS.json # Progress tracking
```

## Configuration Files

**keywords.json** - Search terms and rotation rules:
- `core_keywords`: Known pain language (66%)
- `discovery_keywords`: LLM-learned terms (34%)
- `site_targets`: Where to search
- `rotation`: Query count, cooldown, limits

**focus.txt** - Current business priorities (plain text)

## Database Tables

- `raw_crawl` - Scraped pages
- `extracted_signals` - LLM-extracted signals
- `credibility_scores` - Sales pitch detection (NEW)
- `verified_signals` - Verification results
- `analysis_results` - Pattern analysis
- `briefs` - Generated reports
- `feedback` - User ratings
- `keyword_history` - Performance tracking
- `query_log` - What was searched
- `discovery_queue` - Thread/comment leads (NEW)

## Common Issues

**"Module not found"**: Add to PYTHONPATH
```bash
export PYTHONPATH=/home/pi/swedish-ai:$PYTHONPATH
```

**"Database locked"**: SQLite timeout
```bash
# Check for running processes
ps aux | grep python
```

**"Rate limited by Google"**: Too many queries
```bash
# Reduce query count in config/keywords.json
# Or add random delays
```

**"Claude API quota exceeded"**: Daily limit hit
```bash
# Check usage: grep "claude" logs/*.log | grep -c "API call"
# Reduce pages per query or skip days
```

## Next Steps

1. **Pull latest changes**: `git pull`
2. **Check implementation status**: `cat IMPLEMENTATION_STATUS.json`
3. **Start with Step 1.1**: Reduce query count to 20
4. **Follow atomic steps**: Each is independent and testable
5. **Run tests after each change**: `pytest tests/ -v`
6. **Commit frequently**: `git commit -m "Step X.Y: description"`

## Getting Help

- **System design**: See `docs/smb-intelligence-system-description.md`
- **Implementation steps**: See `docs/implementation/IMPLEMENTATION_PLAN.md`
- **Schema reference**: See `docs/schemas/ALL_SCHEMAS.json`
- **Prompt templates**: See `docs/prompts/ALL_PROMPTS.md`

## Critical Reminders

⚠️ **Hallucination Prevention**: LLMs never touch the internet directly  
⚠️ **Schema Validation**: All LLM outputs must be JSON  
⚠️ **Citation Required**: Every claim must trace to a verified source  
⚠️ **Test Everything**: Run tests before committing

---

Last updated: 2025-02-18
