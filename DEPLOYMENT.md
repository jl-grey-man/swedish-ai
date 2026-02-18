# Swedish AI - Deployment Instructions
**Generated**: 2025-02-18

## What's Been Implemented

### ✅ Phase 1: Foundation
- Query count reduced from 60 to 20 (67% cost reduction)
- JSON schema validation for all LLM calls
- Comprehensive test suite with pytest
- Progress tracking system

### ✅ Phase 2: Credibility Filter  
- Sales pitch detection (blocks Brand Studio, sponsored content)
- Geographic filtering (Nordic countries only)
- Database tables: `credibility_scores`, `discovery_suggestions`
- Deterministic pattern matching (no LLM needed)

### 📦 New Discovery Query Storage
Suggested queries are now saved to the database:
- Quality audit agent → suggests new queries
- Keyword evolution → learns from signals
- Query builder → pulls from suggestions table

---

## Deployment Options

### Option A: Direct Git Push (Fastest)

If you have the repository cloned locally:

```bash
# On your machine/Raspberry Pi
cd /path/to/swedish-ai

# Fetch the changes
git fetch origin

# OR if you want to manually apply the commits:
# The changes are in /tmp/swedish-ai on Claude's computer
# You can copy the changed files over

# Push to GitHub
git push origin main
```

### Option B: Transfer Bundle (For Raspberry Pi)

I've created a complete bundle at `/tmp/swedish-ai-update-20260218.tar.gz`

**Step 1: Transfer to Raspberry Pi**
```bash
# From your current machine (if this is not the Pi):
scp /tmp/swedish-ai-update-20260218.tar.gz pi@raspberrypi.local:/home/pi/

# Or use any other transfer method (USB, etc.)
```

**Step 2: Extract on Raspberry Pi**
```bash
# SSH to Raspberry Pi
ssh pi@raspberrypi.local

# Backup existing installation
cd /home/pi
mv swedish-ai swedish-ai.backup.$(date +%Y%m%d)

# Extract new version
mkdir swedish-ai
cd swedish-ai
tar -xzf ../swedish-ai-update-20260218.tar.gz

# Initialize database with new tables
python3 phases/database.py

# Or apply migration if you already have data
sqlite3 /mnt/storage/swedish-ai/smb.db < migrations/002_add_credibility.sql
```

**Step 3: Test Installation**
```bash
cd /home/pi/swedish-ai

# Run tests
pip3 install pytest --break-system-packages
pytest tests/ -v

# Should see all tests passing:
# ✓ test_llm_utils.py - 6 tests
# ✓ test_credibility.py - 9 tests

# Test query builder (should show 20 queries)
python3 phases/query_builder.py
```

**Step 4: Push to GitHub**
```bash
cd /home/pi/swedish-ai

# Set up git credentials (one-time setup)
git config user.email "your-email@example.com"
git config user.name "Your Name"

# Set up authentication (choose one):

# OPTION 1: Personal Access Token (recommended)
# 1. Go to: https://github.com/settings/tokens
# 2. Generate new token (classic)
# 3. Select: repo (all permissions)
# 4. Copy token
# 5. When pushing, use token as password

# OPTION 2: SSH key (more secure)
ssh-keygen -t ed25519 -C "your-email@example.com"
cat ~/.ssh/id_ed25519.pub
# Copy this and add to: https://github.com/settings/keys
git remote set-url origin git@github.com:jl-grey-man/swedish-ai.git

# Push changes
git push origin main

# Or use the helper script:
./scripts/push_to_github.sh
```

---

## File Summary

### New Files
```
phases/llm_utils.py                    # JSON validation for LLM calls
phases/phase2_5_credibility.py         # Credibility filter
tests/conftest.py                      # Test configuration
tests/test_llm_utils.py                # LLM utility tests
tests/test_credibility.py              # Credibility filter tests
migrations/002_add_credibility.sql     # Database migration
docs/QUICK_START.md                    # Quick reference guide
docs/implementation/IMPLEMENTATION_PLAN.md  # Atomic steps
docs/schemas/ALL_SCHEMAS.json          # JSON schemas
docs/prompts/ALL_PROMPTS.md            # System prompts
scripts/mark_step_complete.sh          # Progress tracker
scripts/push_to_github.sh              # Push helper
IMPLEMENTATION_STATUS.json             # Current progress
README_IMPLEMENTATION.md               # Implementation guide
```

### Modified Files
```
config/keywords.json                   # queries_per_run: 60 → 20
phases/database.py                     # New tables and indexes
```

### Backup Files Created
```
config/keywords.json.backup            # Original config (60 queries)
```

---

## Verification Steps

After deployment, verify everything works:

### 1. Check Configuration
```bash
cd /home/pi/swedish-ai

# Verify query count
python3 -c "
import json
with open('config/keywords.json') as f:
    print('Query count:', json.load(f)['rotation']['queries_per_run'])
"
# Should output: Query count: 20
```

### 2. Check Database
```bash
# Verify new tables exist
sqlite3 /mnt/storage/swedish-ai/smb.db << 'EOF'
.tables
SELECT name FROM sqlite_master WHERE type='table' AND name IN ('credibility_scores', 'discovery_suggestions');
EOF
# Should show both tables
```

### 3. Run Tests
```bash
pytest tests/ -v

# All tests should pass:
# tests/test_llm_utils.py::test_validate_schema_valid ✓
# tests/test_llm_utils.py::test_validate_schema_missing_field ✓
# tests/test_llm_utils.py::test_validate_schema_wrong_type ✓
# tests/test_llm_utils.py::test_validate_schema_nullable ✓
# tests/test_llm_utils.py::test_validate_schema_array ✓
# tests/test_llm_utils.py::test_validate_schema_object ✓
# tests/test_credibility.py::test_detects_brand_studio ✓
# tests/test_credibility.py::test_detects_annons ✓
# tests/test_credibility.py::test_detects_sponsored_url ✓
# tests/test_credibility.py::test_allows_normal_swedish_content ✓
# tests/test_credibility.py::test_detects_non_nordic_geography ✓
# tests/test_credibility.py::test_accepts_danish_content ✓
# tests/test_credibility.py::test_accepts_norwegian_content ✓
# tests/test_credibility.py::test_accepts_swedish_reddit ✓
# tests/test_credibility.py::test_rejects_singapore_reddit ✓
```

### 4. Test Individual Phases
```bash
# Query generation (should show 20 queries)
python3 phases/query_builder.py

# Credibility filter (requires existing data)
python3 phases/phase2_5_credibility.py

# Check progress
cat IMPLEMENTATION_STATUS.json
```

---

## Next Steps After Deployment

### Immediate (Not Yet Implemented)
**Step 2.3**: Integrate Phase 2.5 into pipeline
- Edit `run_pipeline.py` to call credibility check
- Edit `phase3_verify.py` to filter by verdict

### This Week
**Phase 3**: 6-month recency filter
- Improved date extraction from HTML/meta tags
- Reject signals older than 180 days

**Phase 4**: Quality audit agent
- Analyzes brief quality after each run
- Detects sales pitches that slipped through
- Auto-suggests discovery queries

### Later
- Nordic language expansion (DA, NO, FI, IS)
- Thread discovery (LinkedIn comments, Reddit replies)
- Deep research agent (investigates trends)
- Trend tracking (pattern detection over time)

---

## Rollback Plan

If something breaks:

```bash
# Restore previous version
cd /home/pi
rm -rf swedish-ai
mv swedish-ai.backup.$(date +%Y%m%d) swedish-ai

# Or restore specific files
cp swedish-ai.backup.$(date +%Y%m%d)/config/keywords.json swedish-ai/config/

# Or restore database
sqlite3 /mnt/storage/swedish-ai/smb.db < backup_YYYYMMDD.sql
```

---

## Support Resources

All documentation is in the repository:

- **Quick Start**: `docs/QUICK_START.md`
- **Implementation Plan**: `docs/implementation/IMPLEMENTATION_PLAN.md`  
- **JSON Schemas**: `docs/schemas/ALL_SCHEMAS.json`
- **System Prompts**: `docs/prompts/ALL_PROMPTS.md`
- **Implementation Guide**: `README_IMPLEMENTATION.md`

---

## Performance Impact

### Cost Reduction
- **Before**: 60 queries → ~300 pages → ~$0.90/run
- **After**: 20 queries → ~100 pages → ~$0.30/run
- **Savings**: 67% reduction

### Quality Improvement
Based on current brief analysis (2025-02-18):
- **Sales pitches**: ~40% of top signals → Will be blocked
- **Geographic violations**: ~20% → Will be blocked
- **Expected improvement**: 2-3x more actionable leads

### API Usage
```
Per run (20 queries):
- Google searches: 20 (free, but rate-limited)
- Page fetches: ~100 HTTP requests
- Claude extraction: ~100 API calls (~$0.30)
- Claude analysis: 1 API call (~$0.01)
- Claude brief: 1 API call (~$0.01)
- Total: ~$0.32/run

Per month (daily):
- ~30 runs × $0.32 = ~$9.60/month
```

---

## Troubleshooting

### Tests Fail
```bash
# Install missing dependencies
pip3 install pytest --break-system-packages

# Check Python path
export PYTHONPATH=/home/pi/swedish-ai:$PYTHONPATH
```

### Database Errors
```bash
# Check if database exists
ls -l /mnt/storage/swedish-ai/smb.db

# Re-initialize (CAUTION: deletes data)
rm /mnt/storage/swedish-ai/smb.db
python3 phases/database.py

# Or apply migration to existing database
sqlite3 /mnt/storage/swedish-ai/smb.db < migrations/002_add_credibility.sql
```

### Git Push Fails
```bash
# Check authentication
git config --list | grep user

# Test GitHub connection
ssh -T git@github.com

# Use helper script
./scripts/push_to_github.sh
```

---

**Questions?** Check the docs or run:
```bash
cat docs/QUICK_START.md
cat IMPLEMENTATION_STATUS.json
```
