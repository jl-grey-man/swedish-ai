# Swedish AI Intelligence System - Atomic Implementation Plan

**Last Updated**: 2025-02-18  
**Status**: Phase 0 - Foundation

## Overview

This plan breaks down the implementation into atomic, testable steps. Each step can be completed and verified independently before moving to the next.

**Current Query Count**: 20 (reduced from 60 for testing)  
**Repository**: https://github.com/jl-grey-man/swedish-ai

---

## Phase 0: Project Setup ✓

### Step 0.1: Reduce Query Count ✓
**Status**: COMPLETE  
**Changes**: `config/keywords.json` - queries_per_run: 60 → 20  
**Test**: Run `python phases/query_builder.py` - should generate exactly 20 queries

### Step 0.2: Documentation Structure ✓
**Status**: COMPLETE  
**Changes**: Created `docs/` structure with implementation, schemas, prompts  
**Files**: This file, QUICK_START.md, implementation tracking

---

## Phase 1: Foundation (Anti-Hallucination Core)

### Step 1.1: LLM JSON Utility ⏳
**File**: `phases/llm_utils.py`  
**Purpose**: Force all LLM outputs to validated JSON schemas  
**Test**: `python phases/llm_utils.py` - should pass self-test  
**Dependencies**: None  
**Estimated time**: 10 minutes

### Step 1.2: Test Suite Foundation ⏳
**File**: `tests/conftest.py`, `tests/test_llm_utils.py`  
**Purpose**: Test infrastructure for all subsequent changes  
**Test**: `pytest tests/ -v` - all tests pass  
**Dependencies**: pytest installed  
**Estimated time**: 15 minutes

---

## Phase 2: Credibility Filter (Block Sales Pitches)

### Step 2.1: Deterministic Sponsored Content Detection ⏳
**File**: `phases/phase2_5_credibility.py`  
**Purpose**: Catch obvious sales pitches without LLM  
**Test**: Catches "Brand Studio", "/brandstudio/" patterns  
**Dependencies**: Step 1.1 (llm_utils)  
**Estimated time**: 20 minutes

### Step 2.2: Credibility Database Schema ⏳
**File**: `database_migration_2_5.sql`  
**Purpose**: Store credibility scores  
**Test**: Can insert and query credibility_scores  
**Dependencies**: None  
**Estimated time**: 10 minutes

### Step 2.3: Integrate Credibility into Pipeline ⏳
**File**: `run_pipeline.py`, `phases/phase3_verify.py`  
**Purpose**: Phase 2.5 runs after extraction, before verification  
**Test**: Pipeline runs Phase 2.5, only "accept" signals verified  
**Dependencies**: Steps 2.1, 2.2  
**Estimated time**: 15 minutes

---

## Phase 3: Recency Filter (6-Month Limit)

### Step 3.1: Improved Date Extraction ⏳
**File**: `phases/date_utils.py`  
**Purpose**: Better date detection from Swedish content  
**Test**: Parses "15 februari 2025", HTML meta tags, relative dates  
**Dependencies**: None  
**Estimated time**: 25 minutes

### Step 3.2: Add 6-Month Filter to Verification ⏳
**File**: `phases/phase3_verify.py`  
**Purpose**: Reject signals older than 6 months  
**Test**: Old test signal gets rejected  
**Dependencies**: Step 3.1  
**Estimated time**: 20 minutes

---

## Phase 4: Suggested Query Tracking (NEW)

### Step 4.1: Add suggested_queries Table ⏳
**File**: `database_migration_4_1.sql`  
**Purpose**: Save LLM-suggested keywords for review  
**Test**: Can insert and query suggested queries  
**Dependencies**: None  
**Estimated time**: 10 minutes

### Step 4.2: Update Keyword Evolution to Save Suggestions ⏳
**File**: `phases/keyword_evolution.py`  
**Purpose**: Don't auto-add keywords, save for manual review  
**Test**: Run evolution, check suggested_queries table  
**Dependencies**: Step 4.1  
**Estimated time**: 15 minutes

### Step 4.3: Create Keyword Review CLI ⏳
**File**: `scripts/review_keywords.py`  
**Purpose**: Review and approve/reject suggested keywords  
**Test**: Can approve keyword, it gets added to keywords.json  
**Dependencies**: Step 4.2  
**Estimated time**: 20 minutes

---

## Testing Strategy

Each phase has its own tests:

```bash
# Run all tests
pytest tests/ -v

# Run specific phase
pytest tests/test_credibility.py -v
pytest tests/test_date_extraction.py -v
```

---

## Success Metrics

**Week 1 (Phases 0-2)**:
- [ ] Pipeline runs without errors
- [ ] Credibility filter blocks sales pitches
- [ ] Zero "Brand Studio" in briefs
- [ ] 20 queries complete in <10 minutes

**Week 2 (Phase 3)**:
- [ ] No signals older than 6 months
- [ ] Date extraction >80% success rate

**Week 3 (Phases 4-5)**:
- [ ] 10+ keyword suggestions generated
- [ ] First actionable lead identified

**Week 4 (Optimization)**:
- [ ] Increase queries to 30 (if quality holds)
- [ ] 3-5 leads per week

---

See `/IMPLEMENTATION_STATUS.json` for current progress tracking.
