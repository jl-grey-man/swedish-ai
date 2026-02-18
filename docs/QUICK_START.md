# Quick Start for Claude Code on Raspberry Pi

## Current System State (2025-02-18)

**Repository**: `/home/pi/swedish-ai` (or wherever you cloned it)  
**Database**: `/mnt/storage/swedish-ai/smb.db`  
**Query Count**: 20 per run (reduced for testing)

---

## What's Working Now

✓ **Phase 1**: Crawl (Google dorking + page fetching)  
✓ **Phase 2**: Extract (LLM signal extraction)  
✓ **Phase 3**: Verify (deterministic validation)  
✓ **Phase 4**: Analyze (LLM pattern recognition)  
✓ **Phase 5**: Brief (LLM report generation)  
✓ **Phase 6**: Keyword Evolution (LLM keyword learning)

---

## What Needs Building

⏳ **Phase 2.5**: Credibility Check (block sales pitches)  
⏳ **Phase 3 Enhancement**: 6-month recency filter  
⏳ **Phase 4**: Suggested query tracking (save LLM suggestions)  
⏳ **Phase 6**: Quality Audit (self-improvement loop)

**Full plan**: See `docs/implementation/IMPLEMENTATION_PLAN.md`

---

## Quick Commands

```bash
# Check implementation status
cat IMPLEMENTATION_STATUS.json

# Run full pipeline
python run_pipeline.py

# Test specific phase
python phases/phase1_crawl.py
python phases/phase2_extract.py

# Run tests
pytest tests/ -v

# Generate queries (test)
python phases/query_builder.py

# Review suggested keywords (after Phase 4)
python scripts/review_keywords.py list

# Mark step complete
./scripts/mark_step_complete.sh 1.1 "Completed llm_utils"
```

---

## Current Issues (Known)

1. **Sales pitches passing through**: Need Phase 2.5 credibility filter
2. **Old content included**: Need recency filter in Phase 3
3. **Auto-added keywords**: Need manual review system (Phase 4)
4. **No quality feedback**: Need audit agent (Phase 6)

---

## Next Immediate Steps

1. **Start with Phase 1.1**: Create `phases/llm_utils.py`
2. **Test it**: `python phases/llm_utils.py`
3. **Mark complete**: `./scripts/mark_step_complete.sh 1.1 "LLM utils working"`
4. **Move to 1.2**: Set up test suite

**Estimated time to Phase 2 complete**: ~2 hours  
**Estimated time to production-ready**: ~5-6 hours total

---

## File Structure

```
swedish-ai/
├── phases/                    # Pipeline phases
│   ├── phase1_crawl.py       # ✓ Working
│   ├── phase2_extract.py     # ✓ Working
│   ├── phase2_5_credibility.py  # ⏳ Need to build
│   ├── phase3_verify.py      # ✓ Working (needs enhancement)
│   ├── phase4_analyze.py     # ✓ Working
│   ├── phase5_brief.py       # ✓ Working
│   ├── keyword_evolution.py  # ✓ Working (needs enhancement)
│   └── llm_utils.py          # ⏳ Need to build
├── config/
│   ├── keywords.json         # ✓ Updated to 20 queries
│   └── geography.json        # ⏳ For Nordic expansion
├── docs/
│   ├── QUICK_START.md        # ← You are here
│   ├── implementation/
│   │   └── IMPLEMENTATION_PLAN.md
│   ├── schemas/
│   │   └── ALL_SCHEMAS.json
│   └── prompts/
│       └── ALL_PROMPTS.md
├── scripts/
│   ├── mark_step_complete.sh
│   └── review_keywords.py    # ⏳ Need to build
├── tests/
│   ├── conftest.py           # ⏳ Need to build
│   ├── test_llm_utils.py     # ⏳ Need to build
│   └── test_credibility.py   # ⏳ Need to build
├── run_pipeline.py           # ✓ Main entry point
├── IMPLEMENTATION_STATUS.json # Track progress
└── PROJECT.md                # Full system spec
```

---

## Getting Help

1. **Check implementation plan**: `docs/implementation/IMPLEMENTATION_PLAN.md`
2. **Check current status**: `cat IMPLEMENTATION_STATUS.json`
3. **Read full spec**: `PROJECT.md`
4. **Open GitHub issue**: https://github.com/jl-grey-man/swedish-ai/issues

---

## Safety Notes

- **Always backup database** before migrations: `cp smb.db smb.db.backup`
- **Test each phase** before running full pipeline
- **Monitor first 3 runs** after changes
- **Start with 20 queries**, increase only if quality is good
- **Review suggested keywords** before approving

---

**Last Updated**: 2025-02-18  
**Status**: Ready for Phase 1 implementation
