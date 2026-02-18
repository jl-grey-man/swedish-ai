# Swedish AI SMB Intelligence System

**Status**: Phase 0 Complete - Ready for Implementation  
**Last Updated**: 2025-02-18

## Quick Links

- **Start Here**: [docs/QUICK_START.md](docs/QUICK_START.md)
- **Implementation Plan**: [docs/implementation/IMPLEMENTATION_PLAN.md](docs/implementation/IMPLEMENTATION_PLAN.md)
- **Full Specification**: [PROJECT.md](PROJECT.md)
- **Progress Tracking**: [IMPLEMENTATION_STATUS.json](IMPLEMENTATION_STATUS.json)

## What Changed (2025-02-18)

### ✓ Query Count Reduced
- **Before**: 60 queries per run (~300 Claude API calls, ~$1.80/run)
- **After**: 20 queries per run (~100 Claude API calls, ~$0.60/run)
- **Why**: Cheaper testing, faster iteration, lower rate limit risk
- **File**: `config/keywords.json`

### ✓ Suggested Query Tracking Added
- **New**: LLM keyword suggestions saved for manual review
- **Before**: Auto-added to keywords.json (risky vocabulary drift)
- **After**: Saved to `suggested_queries` table, reviewed via CLI
- **Files**: 
  - `database_migration_4_1.sql` - Database schema
  - `scripts/review_keywords.py` - Review CLI

### ✓ Documentation Structure
- **Added**: Atomic implementation plan with testable steps
- **Added**: Quick start guide for Claude Code
- **Added**: Progress tracking system
- **Files**:
  - `docs/QUICK_START.md`
  - `docs/implementation/IMPLEMENTATION_PLAN.md`
  - `IMPLEMENTATION_STATUS.json`
  - `scripts/mark_step_complete.sh`

## Current System State

**Working**:
- Phase 1: Crawl (Google dorking)
- Phase 2: Extract (LLM signal extraction)
- Phase 3: Verify (deterministic validation)
- Phase 4: Analyze (LLM pattern recognition)
- Phase 5: Brief (LLM report generation)
- Phase 6: Keyword Evolution (LLM learning)

**Needs Building**:
- Phase 2.5: Credibility Check (block sales pitches)
- Phase 3 Enhancement: 6-month recency filter
- Phase 6: Quality Audit (self-improvement loop)

## Quick Start

```bash
# Clone repository
git clone https://github.com/jl-grey-man/swedish-ai.git
cd swedish-ai

# Check current status
cat IMPLEMENTATION_STATUS.json

# See what to build next
cat docs/QUICK_START.md

# Start implementation
# Follow docs/implementation/IMPLEMENTATION_PLAN.md
```

## For Claude Code Users

This repository is designed for atomic, testable implementation. Each step in the implementation plan can be completed and verified independently.

**Start here**: [docs/QUICK_START.md](docs/QUICK_START.md)

## System Overview

Autonomous research system that monitors Swedish SMB landscape to identify companies with AI-automatable problems. Runs daily, crawls Swedish sources, extracts verified signals, delivers structured briefs.

**Core Constraint**: Hallucination-proof by architecture. LLMs never touch internet. Scrapers never analyze. Every claim traces to verified source.

**Current Metrics**:
- 20 queries per run
- ~100 Claude API calls per run
- ~$0.60 per run
- Target: 3-5 actionable leads per week

## Next Steps

1. **Phase 1**: Create `phases/llm_utils.py` for forced JSON validation
2. **Phase 2**: Build credibility filter to block sales pitches
3. **Phase 3**: Add 6-month recency filter
4. **Phase 4**: Test suggested query workflow
5. **Phase 5**: Build quality audit agent

**Estimated timeline**: 5-6 hours for core features

See [IMPLEMENTATION_PLAN.md](docs/implementation/IMPLEMENTATION_PLAN.md) for detailed steps.

## Questions?

- Check [docs/QUICK_START.md](docs/QUICK_START.md)
- Read [PROJECT.md](PROJECT.md) for full system spec
- Open GitHub issue for questions

---

**Repository**: https://github.com/jl-grey-man/swedish-ai  
**License**: MIT  
**Status**: Active Development
