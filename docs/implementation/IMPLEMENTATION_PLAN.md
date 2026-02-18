# Atomic Implementation Plan

Each step is independent, testable, and can be completed before moving to the next.

## Progress Tracking

Check: `cat IMPLEMENTATION_STATUS.json`  
Update: `./scripts/mark_step_complete.sh <step> "<note>"`

---

## Phase 0: Setup

### 0.1: Extract Documentation ✓
- Tarball created and transferred
- Documentation in docs/

### 0.2: Set Up Tracking
- Create IMPLEMENTATION_STATUS.json
- Create mark_step_complete.sh script
- **Time**: 5 min | **Risk**: None

---

## Phase 1: Foundation (Reduce & Stabilize)

### 1.1: Reduce Query Count to 20 ⭐ START HERE
**Goal**: Lower cost and Google rate limit risk

**Why first**: Cheaper testing, faster iteration, less blocking

**Steps**:
```bash
# Backup config
cp config/keywords.json config/keywords.json.backup

# Update query count
jq '.rotation.queries_per_run = 20' config/keywords.json > tmp.json
mv tmp.json config/keywords.json

# Verify
jq '.rotation' config/keywords.json
```

**Test**:
```bash
python phases/query_builder.py
# Expected: "Generated 20 queries: 13 core, 7 discovery"
```

**Acceptance**:
- [ ] Config updated
- [ ] Generates exactly 20 queries
- [ ] ~13 core, ~7 discovery split

**Time**: 5 min | **Risk**: None (reversible)

---

### 1.2: Add JSON Schema Validation
**Goal**: Force structured LLM outputs

**Why second**: Foundation for all LLM calls

**Implementation**: Create `phases/llm_utils.py`

**Test**:
```bash
python phases/llm_utils.py
# Should run test successfully
```

**Acceptance**:
- [ ] llm_utils.py created
- [ ] Test passes
- [ ] Can import successfully

**Time**: 10 min | **Risk**: Low

---

### 1.3: Create Test Suite
**Goal**: Safety net for changes

**Implementation**:
```bash
pip3 install pytest --break-system-packages
mkdir -p tests
# Create conftest.py and test files
```

**Test**:
```bash
pytest tests/ -v
```

**Acceptance**:
- [ ] Pytest installed
- [ ] tests/ directory created
- [ ] All tests pass

**Time**: 15 min | **Risk**: None

---

## Phase 2: Credibility Filter

### 2.1: Deterministic Sponsored Content Detection ⭐ HIGH PRIORITY
**Goal**: Block obvious sales pitches (Jacob Wiksell, Lucas Krøll types)

**Why first in Phase 2**: Fastest win, blocks 40% of bad signals

**Implementation**: Create `phases/phase2_5_credibility.py`

**Patterns to detect**:
- "Brand Studio", "i samarbete med"
- "annons", "sponsored", "paid partnership"
- URL: /brandstudio/, /annons/

**Test**:
```bash
pytest tests/test_credibility.py -v
```

**Acceptance**:
- [ ] Detects sponsored content
- [ ] Catches URL patterns
- [ ] Tests pass

**Time**: 20 min | **Risk**: Low

---

### 2.2: Add Credibility Database Schema
**Goal**: Store credibility scores

**Implementation**:
```bash
sqlite3 /mnt/storage/swedish-ai/smb.db < database_migration_2_5.sql
```

**Test**:
```bash
sqlite3 /mnt/storage/swedish-ai/smb.db \
  "SELECT sql FROM sqlite_master WHERE name='credibility_scores';"
```

**Acceptance**:
- [ ] Table created
- [ ] Indexes created
- [ ] Can insert test row

**Time**: 10 min | **Risk**: Low (backup first)

---

### 2.3: Integrate Credibility into Pipeline
**Goal**: Phase 2.5 runs after extraction

**Changes**:
- Update `run_pipeline.py` to call phase 2.5
- Update `phase3_verify.py` to only process "accept" signals

**Test**:
```bash
python phases/phase2_extract.py
python phases/phase2_5_credibility.py
python phases/phase3_verify.py
```

**Acceptance**:
- [ ] Phase 2.5 runs in pipeline
- [ ] "reject" signals excluded from brief
- [ ] Integration works

**Time**: 15 min | **Risk**: Medium (test thoroughly)

---

## Phase 3: Recency Filter

### 3.1: Improve Date Extraction
**Goal**: Better date detection (HTML meta tags, Swedish formats)

**Implementation**: Update `phase1_crawl.py::extract_date_from_text()`

**Test**:
```bash
pytest tests/test_date_extraction.py -v
```

**Acceptance**:
- [ ] Parses HTML meta tags
- [ ] Handles Swedish month names
- [ ] Tests pass

**Time**: 25 min | **Risk**: Low

---

### 3.2: Add 6-Month Filter ⭐ HIGH PRIORITY
**Goal**: Reject signals >6 months old

**Implementation**: Update `phase3_verify.py` recency check

**Test**: Create test signal with old date, verify it's rejected

**Acceptance**:
- [ ] Signals >180 days rejected
- [ ] content_age_days stored
- [ ] Test passes

**Time**: 20 min | **Risk**: Low

---

## Phase 4: Quality Audit Agent (HIGH VALUE)

### 4.1: Create Audit Schema
**Goal**: Define JSON structure for quality reports

**Implementation**: Create `phases/audit_schemas.py`

**Time**: 10 min | **Risk**: None

---

### 4.2: Implement Audit Agent
**Goal**: Analyze brief quality after each run

**Features**:
- Detect sales pitches that slipped through
- Find geographic violations
- Identify stale data
- Suggest improvements
- Propose new features

**Implementation**: Create `phases/phase6_quality_audit.py`

**Time**: 45 min | **Risk**: Low

---

### 4.3: Store Suggested Discovery Queries
**Goal**: Save agent's query suggestions for next run

**Implementation**:
```sql
CREATE TABLE discovery_suggestions (
    id INTEGER PRIMARY KEY,
    source TEXT,  -- 'quality_audit', 'keyword_evolution', 'manual'
    query_text TEXT NOT NULL,
    reason TEXT,
    priority REAL DEFAULT 0.5,
    created_at TEXT DEFAULT (datetime('now')),
    used_at TEXT,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'used', 'retired'))
);
```

**Integration**: query_builder.py pulls from this table for 34% discovery

**Time**: 20 min | **Risk**: Low

---

## Phase 5: Nordic Expansion (Optional)

### 5.1: Add Geography Config
**Goal**: Support Denmark, Norway, Finland, Iceland

**Implementation**: Create `config/geography.json`

**Time**: 5 min | **Risk**: None

---

### 5.2: Update Credibility for Nordic Languages
**Goal**: Accept da.linkedin.com, no.linkedin.com, etc.

**Time**: 15 min | **Risk**: Low

---

## Phase 6: Thread Discovery (34% Enhancement)

### 6.1: LinkedIn Comment Extraction
**Goal**: Find companies mentioned in discussion threads

**Implementation**: Create `phases/phase3_5_thread_discovery.py`

**Time**: 30 min | **Risk**: Low

---

## Phase 7: Deep Research (Advanced)

### 7.1: Create Research Queue
**Goal**: Database for triggered research tasks

**Time**: 15 min | **Risk**: Low

---

### 7.2: Implement Research Agent
**Goal**: Execute deep dives when patterns emerge

**Time**: 60 min | **Risk**: Low

---

## Phase 8: Trend Tracking (Advanced)

### 8.1: Create Trend Database
**Goal**: Track patterns over time

**Time**: 20 min | **Risk**: Low

---

### 8.2: Integrate Trends into Audit
**Goal**: Quality agent detects emerging/fading patterns

**Time**: 30 min | **Risk**: Low

---

## Recommended Order

**Week 1 (Foundation)**:
1. Step 1.1: Reduce queries to 20
2. Step 1.2: JSON validation
3. Step 1.3: Test suite
4. Step 2.1: Sponsored detection
5. Step 2.2: Credibility schema
6. Step 2.3: Pipeline integration

**Week 2 (Quality)**:
7. Step 3.1: Better date extraction
8. Step 3.2: 6-month filter
9. Step 4.1-4.3: Quality audit agent

**Week 3+ (Advanced)**:
10. Nordic expansion
11. Thread discovery
12. Deep research
13. Trend tracking

---

## Testing Strategy

After each step:
```bash
# Run tests
pytest tests/ -v

# Check database
sqlite3 /mnt/storage/swedish-ai/smb.db ".tables"

# Test pipeline phase
python phases/phaseX_*.py

# Commit
git add .
git commit -m "Step X.Y: <description>"
git push
```

---

## Rollback Plan

Each step includes backup:
```bash
# Config changes
cp config/keywords.json config/keywords.json.backup

# Database changes
sqlite3 /mnt/storage/swedish-ai/smb.db ".backup backup_$(date +%Y%m%d).db"

# Code changes
git revert <commit-hash>
```

---

Last updated: 2025-02-18
