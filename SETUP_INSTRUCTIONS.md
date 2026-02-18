# Setup Instructions for Claude Code on Raspberry Pi

Hi Claude Code! This is a pre-configured update to the Swedish AI SMB Intelligence System.

## Quick Setup (Choose One Method)

### Method 1: Pull from GitHub (If Already Pushed)

```bash
cd /home/pi/swedish-ai
git pull origin main

# Done! Skip to "Verify Installation" below
```

### Method 2: Fresh Clone (If Pushed)

```bash
cd /home/pi
mv swedish-ai swedish-ai.backup.$(date +%Y%m%d)  # Backup old version
git clone https://github.com/jl-grey-man/swedish-ai.git
cd swedish-ai
```

### Method 3: Extract Tarball (If Transferred)

```bash
cd /home/pi

# Backup existing
mv swedish-ai swedish-ai.backup.$(date +%Y%m%d)

# Extract
mkdir swedish-ai
cd swedish-ai
tar -xzf ../swedish-ai-update-20260218.tar.gz

# Initialize git
git init
git remote add origin https://github.com/jl-grey-man/swedish-ai.git
git add -A
git commit -m "Initial setup from tarball"
```

---

## Verify Installation

```bash
cd /home/pi/swedish-ai

# 1. Check query count (should be 20)
python3 -c "
import json
with open('config/keywords.json') as f:
    print('✓ Query count:', json.load(f)['rotation']['queries_per_run'])
"

# 2. Check new files exist
ls -l phases/phase2_5_credibility.py
ls -l phases/llm_utils.py
ls -l tests/

# 3. Check database tables
python3 -c "
from phases.database import init_db, get_db
init_db()
conn = get_db()
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
table_names = [t[0] for t in tables]
print('✓ credibility_scores:', 'credibility_scores' in table_names)
print('✓ discovery_suggestions:', 'discovery_suggestions' in table_names)
conn.close()
"
```

---

## Install Dependencies

```bash
pip3 install pytest --break-system-packages
```

---

## Run Tests

```bash
cd /home/pi/swedish-ai
pytest tests/ -v
```

**Expected output**:
```
tests/test_llm_utils.py::test_validate_schema_valid ✓
tests/test_llm_utils.py::test_validate_schema_missing_field ✓
tests/test_llm_utils.py::test_validate_schema_wrong_type ✓
tests/test_llm_utils.py::test_validate_schema_nullable ✓
tests/test_llm_utils.py::test_validate_schema_array ✓
tests/test_llm_utils.py::test_validate_schema_object ✓
tests/test_credibility.py::test_detects_brand_studio ✓
tests/test_credibility.py::test_detects_annons ✓
tests/test_credibility.py::test_detects_sponsored_url ✓
tests/test_credibility.py::test_allows_normal_swedish_content ✓
tests/test_credibility.py::test_detects_non_nordic_geography ✓
tests/test_credibility.py::test_accepts_danish_content ✓
tests/test_credibility.py::test_accepts_norwegian_content ✓
tests/test_credibility.py::test_accepts_swedish_reddit ✓
tests/test_credibility.py::test_rejects_singapore_reddit ✓

15 passed in 0.5s ✓
```

---

## What's New

### Phase 1: Foundation ✓
- Query count: 60 → 20 (67% cost reduction)
- JSON validation for all LLM calls
- Test suite with pytest

### Phase 2: Credibility Filter ✓
- Sales pitch detection (blocks Brand Studio, sponsored content)
- Geographic filtering (Nordic only: SE, DK, NO, FI, IS)
- Discovery query storage (quality agent suggestions)

### Database Changes
- New table: `credibility_scores`
- New table: `discovery_suggestions`
- Updated indexes

---

## Next Steps (Not Yet Implemented)

**Step 2.3**: Integrate Phase 2.5 into pipeline

You'll need to:
1. Edit `run_pipeline.py` to call `phase2_5_credibility.py`
2. Edit `phase3_verify.py` to filter by verdict

See: `docs/implementation/IMPLEMENTATION_PLAN.md` for atomic steps

---

## Documentation

All docs are in the repo:
- **QUICK_START.md** - Quick reference
- **DEPLOYMENT.md** - Full deployment guide
- **README_IMPLEMENTATION.md** - What's been built
- **docs/implementation/IMPLEMENTATION_PLAN.md** - Next steps

---

## Current Status

Completed steps: 0.1, 0.2, 1.1, 1.2, 1.3, 2.1, 2.2

Check: `cat IMPLEMENTATION_STATUS.json`

---

## Test the System

```bash
# Test query generation (should show 20 queries)
python3 phases/query_builder.py

# Test credibility filter (needs existing data)
python3 phases/phase2_5_credibility.py

# Run full pipeline
python3 run_pipeline.py
```

---

## Questions?

All answers are in the documentation:
```bash
cat docs/QUICK_START.md
cat DEPLOYMENT.md
cat README_IMPLEMENTATION.md
```

**For implementation steps**: `cat docs/implementation/IMPLEMENTATION_PLAN.md`

---

That's it! The system is ready to run with 20 queries and credibility filtering.
