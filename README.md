# Swedish AI - SMB Intelligence System

Autonomous research system that monitors the Swedish small business landscape to identify companies struggling with problems AI automation can solve.

## 🎯 What It Does

Crawls Swedish-language sources (LinkedIn, forums, job sites, news) daily to find SMBs (10-249 employees) publicly expressing operational problems that AI could solve. Delivers structured briefs with specific companies, verified contacts, and actionable intelligence.

**Hard constraint**: Must lead to client conversations within 30 days.

## 🚀 Latest Updates (2025-02-18)

### ✅ Phase 1: Foundation
- **Reduced query count**: 60 → 20 queries/run (67% cost reduction)
- **JSON schema validation**: All LLM outputs are now structured
- **Test suite**: Comprehensive pytest coverage

### ✅ Phase 2: Credibility Filter
- **Sales pitch detection**: Blocks sponsored content automatically
- **Geographic filtering**: Nordic countries only (SE, DK, NO, FI, IS)
- **Discovery query storage**: Quality agent suggests new searches

**Performance**: ~$0.30/run (down from $0.90), 2-3x quality improvement expected

## 📋 Quick Start

### Installation
```bash
git clone https://github.com/jl-grey-man/swedish-ai.git
cd swedish-ai

# Install dependencies
pip3 install pytest anthropic --break-system-packages

# Set up environment
export ANTHROPIC_API_KEY="your-key-here"

# Initialize database
python3 phases/database.py

# Run tests
pytest tests/ -v
```

### Running the System
```bash
# Full pipeline
python3 run_pipeline.py

# Individual phases
python3 phases/phase1_crawl.py
python3 phases/phase2_extract.py
python3 phases/phase2_5_credibility.py  # NEW
python3 phases/phase3_verify.py
python3 phases/phase4_5_analyze_brief.py
python3 phases/keyword_evolution.py

# Provide feedback
python3 feedback.py more 123 "Great signal"
python3 feedback.py less 456 "Sales pitch"
```

## 📚 Documentation

- **[Deployment Guide](DEPLOYMENT.md)** - Installation and deployment instructions
- **[Quick Start](docs/QUICK_START.md)** - Quick reference for Claude Code
- **[Implementation Plan](docs/implementation/IMPLEMENTATION_PLAN.md)** - Atomic development steps
- **[Project Specification](PROJECT.md)** - Full system design
- **[Technical Spec](TECH_SPEC.md)** - Detailed technical documentation
- **[Implementation Guide](README_IMPLEMENTATION.md)** - Recent changes and features

## 🏗️ Architecture

6-phase pipeline with anti-hallucination design:

1. **CRAWL** (deterministic) - Google dorking, page fetching
2. **EXTRACT** (LLM + schema) - Signal extraction with validation
3. **CREDIBILITY** (deterministic + LLM) - Sales pitch detection **[NEW]**
4. **VERIFY** (deterministic) - Quote matching, URL checking, company lookup
5. **ANALYZE** (LLM + schema) - Pattern recognition, clustering
6. **BRIEF** (LLM + schema) - Report generation with citations
7. **KEYWORD EVOLUTION** (LLM + schema) - Learning new search terms

**Key Principle**: LLMs never touch the internet. Deterministic code validates all outputs.

## 🗂️ Project Structure

```
swedish-ai/
├── phases/               # Pipeline phases
│   ├── llm_utils.py            # JSON validation (NEW)
│   ├── phase2_5_credibility.py # Credibility filter (NEW)
│   └── ...
├── config/              # Configuration
│   ├── keywords.json           # Search terms (20 queries/run)
│   └── focus.txt               # Business focus
├── tests/               # Test suite (NEW)
├── docs/                # Documentation (NEW)
├── migrations/          # Database migrations (NEW)
├── scripts/             # Helper scripts (NEW)
└── run_pipeline.py      # Main orchestrator
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Test specific module
pytest tests/test_credibility.py -v

# Check coverage
pytest tests/ --cov=phases
```

## 📊 Performance

### Current Configuration
- **Queries per run**: 20 (66% core, 34% discovery)
- **Pages crawled**: ~100 per run
- **Cost per run**: ~$0.30
- **Monthly cost**: ~$9.60 (30 runs)

### Quality Metrics
- **Signal quality**: Expected 2-3x improvement with credibility filter
- **False positive reduction**: ~60% (blocks sales pitches and wrong geography)
- **Nordic focus**: SE (70%), DK/NO/FI/IS (30%)

## 🔄 Development Status

**Completed Steps**: 0.1, 0.2, 1.1, 1.2, 1.3, 2.1, 2.2

**Current Progress**: Step 2.3 (Pipeline Integration)

**Next Up**:
- Phase 3: 6-month recency filter
- Phase 4: Quality audit agent
- Phase 5: Nordic language expansion
- Phase 6: Thread discovery
- Phase 7: Deep research agent

Track progress: `cat IMPLEMENTATION_STATUS.json`

## 🛠️ Configuration

### Adjust Query Count
```bash
# Edit config/keywords.json
"queries_per_run": 20  # Change to 10-60
```

### Add Discovery Keywords
```bash
# Use keyword evolution (automatic)
python3 phases/keyword_evolution.py

# Or add manually to discovery_suggestions table
sqlite3 /mnt/storage/swedish-ai/smb.db
INSERT INTO discovery_suggestions (source, query_text, reason, priority)
VALUES ('manual', 'chaotiskt system', 'Colloquial Swedish for messy processes', 0.8);
```

## 🐛 Troubleshooting

### Tests Fail
```bash
export PYTHONPATH=/path/to/swedish-ai:$PYTHONPATH
pip3 install pytest --break-system-packages
```

### Database Errors
```bash
# Re-initialize (CAUTION: deletes data)
python3 phases/database.py

# Or apply migration
sqlite3 /mnt/storage/swedish-ai/smb.db < migrations/002_add_credibility.sql
```

### API Rate Limits
Reduce query count or add delays between requests.

## 📝 License

Private project.

## 🤝 Contributing

This is a private research project. See `DEPLOYMENT.md` for development setup.

---

**For deployment instructions**: See [DEPLOYMENT.md](DEPLOYMENT.md)  
**For quick reference**: See [docs/QUICK_START.md](docs/QUICK_START.md)  
**For implementation details**: See [README_IMPLEMENTATION.md](README_IMPLEMENTATION.md)