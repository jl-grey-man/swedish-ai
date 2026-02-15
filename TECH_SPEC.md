# SMB Intelligence System — Technical Specification

This document contains everything a developer needs to implement the system described in `PROJECT.md`. Read that document first for context, goals, and design rationale.


## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   run_pipeline.py                     │
│              (orchestrator, CLI entry point)           │
├─────────┬─────────┬─────────┬─────────┬─────────┬───┤
│ Phase 1 │ Phase 2 │ Phase 3 │ Phase 4 │ Phase 5 │ 6 │
│ CRAWL   │ EXTRACT │ VERIFY  │ ANALYZE │ BRIEF   │ KW│
│ (det.)  │ (LLM)   │ (det.)  │ (LLM)   │ (LLM)   │(L)│
├─────────┴─────────┴─────────┴─────────┴─────────┴───┤
│                    database.py                        │
│                  SQLite (intel.db)                     │
├──────────────────────────────────────────────────────┤
│               config/                                 │
│   focus.txt  ·  keywords.json                         │
└──────────────────────────────────────────────────────┘

det. = deterministic (no LLM)
LLM  = calls Anthropic API (sandboxed, no internet access)
```

### Directory Structure

```
smb-intel/
├── run_pipeline.py          # Main entry point / orchestrator
├── feedback.py              # CLI tool for signal feedback
├── config/
│   ├── focus.txt            # Operator steering file (plain text)
│   └── keywords.json        # Keyword configuration with 66/34 split
├── phases/
│   ├── database.py          # Schema, init, helpers
│   ├── query_builder.py     # Generates Google dork queries
│   ├── phase1_crawl.py      # Google search + page fetch
│   ├── phase2_extract.py    # LLM extraction agent
│   ├── phase3_verify.py     # Deterministic verification
│   ├── phase4_5_analyze_brief.py  # LLM analysis + brief prompts
│   └── keyword_evolution.py # LLM keyword suggestion + tracking
├── data/
│   ├── intel.db             # SQLite database (created at runtime)
│   └── logs/                # Crawl stats, pipeline logs
├── briefs/                  # Output: daily markdown briefs
├── PROJECT.md
└── TECH_SPEC.md
```


## 2. Database Model

Single SQLite database at `data/intel.db`. WAL journal mode enabled for concurrent read during writes. Foreign keys enforced.

### 2.1 Entity-Relationship Diagram

```
┌──────────────┐     ┌───────────────────┐     ┌──────────────────┐
│  raw_crawl   │────<│ extracted_signals  │────<│ verified_signals  │
│              │  1:N │                   │  1:1 │                  │
│ source_hash  │     │ source_hash (FK)   │     │ signal_id (FK)   │
│ source_url   │     │ signal_type        │     │ quote_check      │
│ raw_text     │     │ person_*           │     │ url_check        │
│ raw_html     │     │ company_*          │     │ company_verified │
│ query_used   │     │ original_quote     │     │ final_status     │
│ keyword_type │     │ expressed_problem  │     └──────────────────┘
└──────────────┘     │ expressed_need     │
                     │ ai_awareness       │     ┌──────────────────┐
                     │ topic_tags (JSON)  │────<│    feedback       │
                     └───────────────────┘  1:N │ signal_id (FK)   │
                                                │ rating           │
┌──────────────────┐                            │ note             │
│  analysis_runs   │                            └──────────────────┘
│ run_date         │
│ problem_clusters │  (all JSON)    ┌──────────────────┐
│ white_spaces     │                │  query_log        │
│ watchlist        │                │ query_text        │
│ sector_patterns  │                │ keyword_type      │
│ discovery_sugg.  │                │ results_count     │
└──────────────────┘                │ run_date          │
                                    └──────────────────┘
┌──────────────────┐
│ keyword_history  │                ┌──────────────────┐
│ keyword          │                │ discovered_sources│
│ keyword_type     │                │ url              │
│ times_used       │                │ hit_count        │
│ hit_rate         │                │ promoted_to_fixed│
│ active           │                └──────────────────┘
└──────────────────┘
```

### 2.2 Table Definitions

#### `raw_crawl` — Phase 1 output. Append-only. Never modified after insertion.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK AUTOINCREMENT | Internal row ID |
| source_hash | TEXT | UNIQUE NOT NULL | SHA-256 of URL + first 500 chars of content, truncated to 16 hex chars |
| source_url | TEXT | NOT NULL | Exact URL as fetched |
| source_domain | TEXT | NOT NULL | Domain from URL, `www.` stripped |
| crawl_timestamp | TEXT | NOT NULL | ISO 8601 UTC timestamp of crawl |
| content_date | TEXT | NULLABLE | Date extracted from page content (best-effort regex) |
| page_title | TEXT | NULLABLE | HTML `<title>` content |
| raw_text | TEXT | NOT NULL | Cleaned text (scripts/nav/footer removed). Max 50,000 chars. |
| raw_html | TEXT | NULLABLE | Original HTML. Max 100,000 chars. |
| query_used | TEXT | NULLABLE | The Google dork query that found this page |
| keyword_type | TEXT | CHECK IN ('core', 'discovery') | Which query pool found this |
| http_status | INTEGER | NULLABLE | HTTP response status code |
| created_at | TEXT | DEFAULT datetime('now') | Row insertion time |

Indexes: `source_hash` (unique), `source_domain`, `crawl_timestamp`

#### `extracted_signals` — Phase 2 output. One or more rows per raw_crawl page.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK AUTOINCREMENT | Signal ID (referenced throughout system) |
| source_hash | TEXT | NOT NULL, FK → raw_crawl.source_hash | Links to source page |
| signal_type | TEXT | CHECK IN ('job_posting', 'social_post', 'news_mention', 'forum_post', 'company_data') | Classification |
| person_name | TEXT | NULLABLE | Full name exactly as written in source |
| person_title | TEXT | NULLABLE | Job title exactly as written |
| person_company | TEXT | NULLABLE | Company associated with person |
| company_name | TEXT | NULLABLE | Company name (may differ from person_company) |
| company_org_number | TEXT | NULLABLE | Swedish org number if in source |
| company_industry | TEXT | NULLABLE | Only if explicitly stated |
| company_employee_count | TEXT | NULLABLE | Only if explicitly stated |
| original_quote | TEXT | NULLABLE | Exact text from source, max 500 chars. Never rewritten. |
| expressed_problem | TEXT | NULLABLE | LLM summary of the problem described |
| expressed_need | TEXT | NULLABLE | LLM summary of what they say they need |
| ai_awareness | TEXT | CHECK IN ('using_ai', 'exploring_ai', 'skeptical', 'unaware', NULL) | AI maturity level |
| topic_tags | TEXT | NULLABLE | JSON array of topic strings |
| extraction_model | TEXT | NULLABLE | LLM model used for extraction |
| created_at | TEXT | DEFAULT datetime('now') | Extraction time |

Indexes: `company_name`, `source_hash`

#### `verified_signals` — Phase 3 output. One row per extracted signal.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK AUTOINCREMENT | Internal ID |
| signal_id | INTEGER | NOT NULL, FK → extracted_signals.id | Which signal was verified |
| quote_check | TEXT | CHECK IN ('passed', 'failed', 'partial') | Fuzzy match result |
| quote_similarity | REAL | NULLABLE | Best similarity score (0.0–1.0) |
| url_check | TEXT | CHECK IN ('live', 'dead', 'redirect', 'timeout') | Source URL status |
| company_verified | INTEGER | DEFAULT 0 | 1 if found on Allabolag.se |
| company_allabolag_data | TEXT | NULLABLE | JSON from Allabolag lookup |
| is_duplicate | INTEGER | DEFAULT 0 | 1 if duplicate of existing signal |
| duplicate_of | INTEGER | NULLABLE | ID of original signal if duplicate |
| final_status | TEXT | CHECK IN ('verified', 'rejected', 'weak') | Downstream eligibility |
| verified_at | TEXT | DEFAULT datetime('now') | Verification time |

Index: `final_status`

#### `analysis_runs` — Phase 4 output. One row per pipeline run.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK AUTOINCREMENT | Run ID |
| run_date | TEXT | NOT NULL | YYYY-MM-DD |
| focus_file_hash | TEXT | NULLABLE | MD5 of focus.txt at analysis time |
| signals_processed | INTEGER | NULLABLE | Total signals input |
| signals_verified | INTEGER | NULLABLE | Verified count |
| problem_clusters | TEXT | NULLABLE | JSON array |
| white_spaces | TEXT | NULLABLE | JSON array |
| watchlist | TEXT | NULLABLE | JSON array |
| sector_patterns | TEXT | NULLABLE | JSON array |
| discovery_suggestions | TEXT | NULLABLE | JSON array |
| keyword_suggestions | TEXT | NULLABLE | JSON array |
| tokens_input_total | INTEGER | NULLABLE | Total input tokens across all LLM calls in this run |
| tokens_output_total | INTEGER | NULLABLE | Total output tokens across all LLM calls in this run |
| created_at | TEXT | DEFAULT datetime('now') | |

#### `feedback` — Operator signal ratings.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK AUTOINCREMENT | |
| signal_id | INTEGER | NULLABLE | References extracted_signals.id |
| analysis_run_id | INTEGER | NULLABLE | Which run's brief |
| rating | TEXT | CHECK IN ('more', 'less') | |
| note | TEXT | NULLABLE | Free-text |
| created_at | TEXT | DEFAULT datetime('now') | |

#### `discovered_sources` — Discovery tracking.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK AUTOINCREMENT | |
| url | TEXT | NOT NULL | Source URL |
| source_type | TEXT | NULLABLE | Category |
| discovered_from_signal | INTEGER | NULLABLE | Which signal led here |
| hit_count | INTEGER | DEFAULT 0 | Verified signals produced |
| promoted_to_fixed | INTEGER | DEFAULT 0 | 1 if graduated |
| active | INTEGER | DEFAULT 1 | |
| created_at | TEXT | DEFAULT datetime('now') | |

#### `query_log` — Search query tracking for rotation and dedup.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK AUTOINCREMENT | |
| query_text | TEXT | NOT NULL | Exact Google query |
| keyword_type | TEXT | CHECK IN ('core', 'discovery') | |
| site_target | TEXT | NULLABLE | |
| results_count | INTEGER | NULLABLE | Google results returned |
| useful_results | INTEGER | DEFAULT 0 | Results producing signals |
| run_date | TEXT | NOT NULL | YYYY-MM-DD |
| created_at | TEXT | DEFAULT datetime('now') | |

Index: `run_date`

#### `keyword_history` — Keyword lifecycle and performance.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK AUTOINCREMENT | |
| keyword | TEXT | NOT NULL | The keyword/phrase |
| keyword_type | TEXT | CHECK IN ('core', 'discovery') | |
| source | TEXT | NULLABLE | 'initial', 'llm_suggested', 'promoted_from_discovery' |
| times_used | INTEGER | DEFAULT 0 | Total query uses |
| times_produced_signal | INTEGER | DEFAULT 0 | Uses that yielded verified signals |
| hit_rate | REAL | DEFAULT 0.0 | produced / used |
| active | INTEGER | DEFAULT 1 | 0 if retired |
| added_date | TEXT | DEFAULT datetime('now') | |
| retired_date | TEXT | NULLABLE | |
| last_used | TEXT | NULLABLE | Timestamp of most recent query use |

Index: `last_used` (for time-based retirement queries)

#### `company_cache` — Allabolag lookup cache to avoid redundant requests.

| Column | Type | Constraints | Description |
|---|---|---|---|
| company_name_lower | TEXT | PRIMARY KEY | Lowercased company name |
| allabolag_data | TEXT | NULLABLE | JSON from Allabolag lookup |
| cache_timestamp | TEXT | NOT NULL | When cached |
| cache_ttl_days | INTEGER | DEFAULT 30 | Days before stale |


## 3. LLM Interface

### 3.1 API Configuration

| Parameter | Value | Notes |
|---|---|---|
| Provider | Anthropic | |
| Model | `claude-sonnet-4-20250514` | Cost/quality balance |
| Max tokens | 2048 (extract), 4096 (analyze/brief), 2048 (keywords) | Per-phase caps |
| Auth | `ANTHROPIC_API_KEY` env var | Must be set before run |
| SDK | `anthropic` Python package | |

All LLM calls go through a single `call_llm(system_prompt, user_prompt, max_tokens)` function in the pipeline orchestrator. Phases define prompts but never call the API directly.

### 3.2 Agent Specifications

#### Agent 1: Extractor (Phase 2)

**Purpose:** Extract structured signals from raw text with anti-hallucination constraints.

**System prompt core rules:**
- ONLY extract information explicitly stated in provided text
- NEVER infer, assume, or generate information not present
- NEVER add context from training data
- Null fields over guessed fields
- Preserve original Swedish for quotes
- Output JSON only

**Expected I/O:** ~1K–8K tokens in → ~200–1K tokens out

**Output schema:**
```json
{
  "signals": [
    {
      "signal_type": "job_posting | social_post | news_mention | forum_post | company_data",
      "person": {
        "name": "string | null",
        "title": "string | null",
        "company": "string | null"
      },
      "company": {
        "name": "string | null",
        "industry": "string | null",
        "employee_count": "string | null"
      },
      "content": {
        "original_quote": "exact copy-paste from source, max 500 chars",
        "topic_tags": ["string"],
        "expressed_problem": "string | null",
        "expressed_need": "string | null",
        "ai_awareness": "using_ai | exploring_ai | skeptical | unaware | null"
      }
    }
  ]
}
```

#### Agent 2: Analyzer (Phase 4)

**Purpose:** Pattern detection, clustering, white space identification.

**System prompt core rules:**
- Every claim references specific signal IDs
- No knowledge beyond provided signals
- Patterns on <3 signals = "weak_signal"
- Respect feedback weighting

**Expected I/O:** ~2K–15K tokens in → ~1K–3K tokens out

**Output schema:**
```json
{
  "problem_clusters": [{
    "name": "string",
    "description": "string",
    "signal_count": 0,
    "signal_ids": [],
    "intensity": "high | medium | low",
    "trend": "growing | stable | shrinking | new",
    "example_quotes": ["string"]
  }],
  "white_spaces": [{
    "problem": "string",
    "signal_ids": [],
    "opportunity_description": "string",
    "estimated_demand": "high | medium | low | unknown"
  }],
  "watchlist_companies": [{
    "company_name": "string",
    "signal_count": 0,
    "signal_ids": [],
    "summary": "string",
    "org_number": "string | null",
    "employee_count": "string | null"
  }],
  "sector_patterns": [{
    "sector": "string",
    "signal_count": 0,
    "dominant_problems": ["string"],
    "ai_readiness": "high | medium | low"
  }],
  "discovery_suggestions": [{
    "source": "string",
    "reason": "string"
  }]
}
```

#### Agent 3: Brief Writer (Phase 5)

**Purpose:** Human-readable daily brief with strict citation.

**System prompt core rules:**
- Every person: name, title, company. No exceptions.
- Every claim: source URL, date. No exceptions.
- Uncitable content excluded.
- Quotes in Swedish, rest in English.
- Fixed section structure.
- Max ~1,500 words.

**Expected I/O:** ~3K–10K tokens in → ~1K–2K tokens out

**Output:** Markdown text (not JSON). Fixed section structure defined in PROJECT.md §5.

#### Agent 4: Keyword Evolver (Phase 6)

**Purpose:** Discover new keywords from signal language, retire underperformers.

**System prompt core rules:**
- Swedish-language keywords only (or English terms common in Swedish business)
- Focus on pain language
- 1–4 words per keyword, 5–15 suggestions per run
- Don't repeat existing keywords
- Also identify retirement candidates

**Expected I/O:** ~1K–5K tokens in → ~300–800 tokens out

**Output schema:**
```json
{
  "new_keywords": [{
    "keyword": "string",
    "reason": "string",
    "derived_from": "string"
  }],
  "retire_candidates": [{
    "keyword": "string",
    "reason": "string"
  }]
}
```

### 3.3 Response Parsing

All LLM responses expected as JSON. Three-layer parser:

1. `json.loads(response.strip())` — direct parse
2. Strip markdown fences (` ```json ` / ` ``` `), then parse
3. Regex extract first `{...}` block, then parse
4. All fail → log warning, return empty, continue pipeline

No LLM failure halts the pipeline. Failed extractions skip the page. Failed analysis/brief → no output that day. Data integrity maintained.

### 3.4 Token Usage Tracking

Three-layer approach, each serving a different purpose:

**Layer 1: Log (always).** Every `call_llm()` reads `response.usage.input_tokens` and `response.usage.output_tokens` from the Anthropic API response and writes them to `pipeline.log` with the phase name. Zero cost. Audit trail for post-run analysis.

**Layer 2: In-memory circuit breaker (during run).** The pipeline orchestrator accumulates a running token total across all LLM calls in the current run. If the total exceeds a configurable soft cap (default: 800K tokens, ~$5), the pipeline:
- Logs a warning
- Skips remaining Phase 2 extractions (the highest-volume phase — one call per page)
- Still runs Phases 4–6 on whatever was already extracted
- Does NOT hard-kill the pipeline

This prevents a runaway crawl day (e.g., Google returns 200 pages instead of 50) from blowing budget, while preserving the analysis of already-extracted data.

**Layer 3: Persist per-run totals.** Add `tokens_input_total` and `tokens_output_total` columns to the `analysis_runs` table. One row per run, capturing the full cost. No new table needed — this is run-level metadata.

```python
# In call_llm():
response = client.messages.create(...)
tokens_in = response.usage.input_tokens
tokens_out = response.usage.output_tokens
log.info(f"[{phase_name}] Tokens: {tokens_in} in, {tokens_out} out")
pipeline_state['token_total'] += tokens_in + tokens_out

if pipeline_state['token_total'] > TOKEN_SOFT_CAP:
    log.warning(f"Token cap reached ({pipeline_state['token_total']}). "
                f"Skipping remaining Phase 2 extractions.")
    pipeline_state['extraction_halted'] = True

return response.content[0].text
```

| Constant | Value | Location |
|---|---|---|
| TOKEN_SOFT_CAP | 800,000 | run_pipeline.py |


## 4. State Management

### 4.1 Principle

State lives in SQLite. Config lives in flat files. No in-memory state survives between runs.

### 4.2 Boundaries

| State | Storage | Modified By |
|---|---|---|
| Crawl data | `raw_crawl` table | Phase 1 (append-only) |
| Signals | `extracted_signals` | Phase 2 (append-only) |
| Verification | `verified_signals` | Phase 3 (append-only) |
| Analysis | `analysis_runs` | Phase 4 (append-only) |
| Feedback | `feedback` | feedback.py CLI (append-only) |
| Query history | `query_log` | Phase 1 (append-only) |
| Keyword stats | `keyword_history` | Phase 1 + 6 (updated) |
| Keyword config | `keywords.json` | Phase 6 (mutated with backup) |
| Focus config | `focus.txt` | Operator manual edit |
| Briefs | `briefs/*.md` | Phase 5 (one per day) |

### 4.3 Run Isolation and Resumability

Each phase commits independently. A crashed run leaves consistent state. Resumability is achieved through LEFT JOIN patterns — each phase queries for items that lack a corresponding row in the next phase's table:

- Phase 1 crash → partial crawl data saved. Next run skips already-crawled URLs (dedup on `source_url` in `raw_crawl`).
- Phase 2 crash → partial extractions saved. Next run query: `SELECT raw_crawl LEFT JOIN extracted_signals WHERE es.id IS NULL` — picks up pages that have no extraction yet. Already-extracted pages are never re-processed, regardless of Phase 3 state.
- Phase 3 crash → partial verifications saved. Next run query: `SELECT extracted_signals LEFT JOIN verified_signals WHERE vs.id IS NULL` — picks up signals with no verification row. Already-verified signals are skipped.
- Phase 4+ crash → no partial state. Rerun generates fresh analysis from all verified data.

Critical: Phase 2 resumability checks against `extracted_signals`, not `verified_signals`. A Phase 3 crash cannot cause Phase 2 to re-extract. The phases are independently resumable.

### 4.4 Keyword Config Safety

Before every Phase 6 mutation:
1. Backup: `keywords.backup_YYYYMMDD_HHMM.json`
2. Modify in-memory copy
3. Write atomically to disk

Any backup can be restored manually.


## 5. Configuration Schemas

### 5.1 `focus.txt`

Plain YAML-like text. Not parsed programmatically — injected raw into LLM prompts. The LLM interprets intent. This means the format is flexible and human-friendly.

### 5.2 `keywords.json`

Parsed by `query_builder.py`. Top-level keys:

```
core_keywords.pain_signals[]        — 15 terms
core_keywords.ai_awareness[]        — 6 terms
core_keywords.business_context[]    — 9 terms
core_keywords.specific_tasks[]      — 13 terms
discovery_keywords.from_signals[]   — starts empty, LLM-populated
discovery_keywords.adjacent_terms[] — 13 seed terms
site_targets{}                      — 10 Google dork prefixes
query_templates.patterns[]          — 5 combination templates
rotation.queries_per_run            — 60
rotation.core_ratio                 — 0.66
rotation.discovery_ratio            — 0.34
rotation.max_per_site               — 15
rotation.cooldown_days_before_reuse — 3
```


## 6. CLI Interface

### 6.1 Pipeline

```
python run_pipeline.py              # Full run (all 6 phases)
python run_pipeline.py --crawl-only # Phase 1 only
python run_pipeline.py --skip-crawl # Phases 2–6 on existing data
python run_pipeline.py --brief-only # Regenerate brief from last analysis

Required env: ANTHROPIC_API_KEY
Exit: 0 success, 1 error
```

### 6.2 Feedback

```
python feedback.py more <signal_id> [note]
python feedback.py less <signal_id> [note]
python feedback.py list
python feedback.py stats
```

### 6.3 Cron

```cron
0 5 * * * cd /path/to/smb-intel && ANTHROPIC_API_KEY=sk-... python3 run_pipeline.py >> data/logs/cron.log 2>&1
```


## 7. Data Flow Details

### 7.1 Phase 1 — Crawl

```
keywords.json → query_builder.py → [60 queries, shuffled]
    │
    For each query:
        Google.se search → parse result URLs
        For each result (max 5):
            Dedup check (source_url in raw_crawl?) → skip if exists
            HTTP GET → BeautifulSoup text extraction
            store_crawl_result() → raw_crawl
            log_query() → query_log
```

**Query split enforcement (how 66/34 is maintained):**

The split is enforced at query count, not keyword pool size. Weights operate *within* a pool, not across pools:

```
Step 1: Hard budget split
  core_count = int(60 * 0.66)     = 39 queries
  discovery_count = 60 - 39       = 21 queries

Step 2: Generate candidates per pool (INDEPENDENTLY)
  core_candidates = build_core_queries(...)          # many candidates
  discovery_candidates = build_discovery_queries(...) # many candidates
  
  Inside build_discovery_queries, the 1.5x/0.3x weights determine
  which KEYWORDS appear in these 21 slots. A 1.5x keyword is more
  likely to be picked than a 0.3x keyword. But there are always
  exactly 21 discovery queries.

Step 3: Truncate each pool to its budget
  final = core_candidates[:39] + discovery_candidates[:21]
```

Whether there are 13 or 40 discovery keywords, the system generates exactly 21 discovery queries. More keywords = each keyword sampled less often within its pool. The weights don't affect the pool boundary — they affect selection probability within the pool.

Rate limits: 2–5s between Google queries (random), 1s between page fetches, 60s pause on suspected CAPTCHA.

### 7.2 Phase 2 — Extract

```
SELECT raw_crawl WHERE no extracted_signals AND length(raw_text) > 100
    │
    For each page:
        Build prompt (hash, URL, title, text[:8000])
        call_llm() → JSON
        parse + validate → store in extracted_signals
```

### 7.3 Phase 3 — Verify

```
SELECT unverified signals (LEFT JOIN)
    │
    For each signal:
        1. Normalize quote + raw_text (NFKC unicode, html.unescape, whitespace collapse)
        2. Fuzzy match normalized quote vs normalized raw_text FROM DATABASE
           (compares LLM output against stored Phase 1 text — no re-fetch)
        3. HTTP HEAD on source_url (liveness only — no content downloaded)
        4. Company cache lookup → if miss AND not stale, Allabolag.se scrape → cache result
        5. Dedup (same person+company, >0.70 quote similarity, 7 days)
        → INSERT verified_signals with final_status
```

**Critical architecture note — two separate checks, often confused:**

- **URL check** = `HTTP HEAD source_url`. Checks if the page still exists (200/301/403 = live, 404 = dead). Does NOT download page content. Does NOT re-read the page text. Answers: "Can the operator click this link?"
- **Quote check** = fuzzy match `extracted_signals.original_quote` against `raw_crawl.raw_text`. Both values already in the database from Phases 1 and 2. No network request involved. Answers: "Did the LLM faithfully extract this quote?"

Encoding drift between fetches is impossible because there is only one content fetch (Phase 1). Phase 3 never downloads page content.

**Text normalization (applied before fuzzy matching):**
1. `html.unescape()` — decode HTML entities
2. `unicodedata.normalize('NFKC')` — canonical Unicode normalization (smart quotes, combining diacritics)
3. `re.sub(r'\s+', ' ')` — collapse all whitespace variants (including `\xa0` non-breaking spaces)
4. `.strip().lower()` — case-insensitive comparison

Normalization is a defensive measure against LLM output formatting differences (e.g., smart quotes in LLM response vs. straight quotes in stored source text). It guards against the LLM, not the internet.

**Allabolag company cache:**
Before scraping Allabolag, check `company_cache` table for a non-stale entry (TTL: 30 days). If cached, use cached data. If miss or stale, scrape and cache result. This prevents redundant lookups when the same company appears in multiple signals.

**Fuzzy match algorithm detail:**
1. Normalize both strings (see above)
2. Exact substring check → similarity 1.0
3. Sliding window: step = quote_len/4, use `SequenceMatcher.ratio()`
4. If quote >50 chars: independently check first half and second half as substrings
5. Both halves found → 0.85; one half found → 0.70

### 7.4 Phase 4 — Analyze

```
SELECT verified/weak signals (limit 200, newest first)
Load: focus.txt, feedback (7 days), previous analysis_run
    │
    Build prompt → call_llm() → parse JSON → INSERT analysis_runs
```

### 7.5 Phase 5 — Brief

```
Latest analysis_run + verified signals (limit 100)
    │
    Build prompt → call_llm() → write briefs/brief_YYYY-MM-DD.md
```

### 7.6 Phase 6 — Keyword Evolution

```
Verified signals (limit 100) + keywords.json + keyword_history
    │
    Build prompt → call_llm() → parse JSON
    Backup keywords.json
    Add new keywords to discovery_keywords.from_signals
    Remove retired keywords from both lists
    Track in keyword_history table
```


## 8. Edge Cases

### 8.1 Crawling

| Case | Handling |
|---|---|
| Google CAPTCHA/block | 0 results in 20 consecutive queries → 60s pause. Persistent → abort crawl, log error. |
| Non-HTML response (PDF, image) | Content-type check. Skip if not text/html or text/plain. |
| Page >50K chars | Truncate raw_text at 50K, raw_html at 100K. |
| Duplicate URL from different queries | source_url dedup before fetch. |
| Paywall/login content | Returns partial. Phase 2 extracts nothing. Phase 3 rejects. Self-cleaning. |
| Non-Swedish content on .se domain | Phase 2 extracts if business-relevant regardless. |
| Allabolag wrong company for fuzzy name | Best-effort. company_verified=0 is safe default. Enrichment only. Results cached (30-day TTL) to avoid redundant lookups for same company across signals. |
| robots.txt blocks source | Currently stated as "respected" but not enforced. TODO: implement or accept. |
| Special chars in keywords break Google syntax | `quote_plus()` on full query. Discovery keywords should be sanitized (strip `"`, `site:`, `-`, `OR`, `AND`). |

### 8.2 Extraction

| Case | Handling |
|---|---|
| Non-JSON LLM response | Three-layer parser (direct → strip markdown → regex). All fail → skip. |
| Hallucinated company name | Phase 3 Allabolag check flags. Quote check also fails if name absent from raw text. |
| Signals with partial data only | Must have `original_quote` or `expressed_problem`. Otherwise dropped at parse. |
| Raw text <100 chars | Filtered out before Phase 2 query. |
| API rate limit / timeout | try/except → empty response → page skipped → retried next run. |

### 8.3 Verification

| Case | Handling |
|---|---|
| Quote reformatted by Google cache | Not applicable — Phase 3 compares against stored `raw_text`, not a re-fetched page. No encoding drift between fetches. Normalization (NFKC + html.unescape) guards against LLM output formatting differences (e.g., smart quotes). |
| URL redirected | HTTP HEAD follows redirects (no content downloaded). Final 200 = "live." This is a liveness check only — Phase 3 never re-fetches page content. Quote verification runs against stored `raw_crawl.raw_text`, not re-downloaded content. |
| Company name spelling variation | Allabolag search returns best match. company_verified=0 safe default. |
| Same person, different quote | Dedup requires person + company + >70% quote sim. Different quotes kept as separate signals. |
| Allabolag down | Exception caught. company_verified stays 0. Signal not rejected. Cached results still available for previously-looked-up companies. |
| Page dead at verify time (was live at crawl) | url_check = "dead" → rejected. Correct: uncitable = excluded. |

### 8.4 Analysis and Brief

| Case | Handling |
|---|---|
| Zero verified signals | Phase 4 returns empty. Phase 5 skipped. No brief. Correct. |
| Unexpected analysis JSON structure | Stored as-is. Brief agent works with whatever it gets. |
| Brief >1500 words | Prompt suggests limit, doesn't enforce. Acceptable. |
| No previous analysis (first run) | Trend comparison section omitted. |
| Feedback references deleted signal | Ignored at analysis join. |

### 8.5 Keywords

| Case | Handling |
|---|---|
| keywords.json corrupted | Restore from most recent backup. |
| LLM suggests existing keyword | Dedup check before adding. |
| Discovery list hits hard cap (40) | LRU eviction: retire least-recently-used keyword with lowest hit rate to make room. |
| Time-based decay | Keywords unused for 30+ days auto-retire regardless of hit rate (insufficient data to evaluate). |
| All discovery keywords underperform | All retired → fewer discovery queries → system turns conservative. Operator should notice and reseed. |
| Keyword breaks Google syntax | Sanitize: strip `"`, `site:`, `-`, `OR`, `AND` from LLM suggestions before adding to config. |
| Keyword pool dilution | Hard cap (40) + time decay + performance retirement prevents individual keywords from being sampled too rarely to evaluate. The 66/34 query count split is enforced at query generation, not keyword pool size — more keywords doesn't change the ratio of core vs discovery queries. |

### 8.6 System

| Case | Handling |
|---|---|
| Pipeline crash mid-run | Each phase commits independently. Resumable (§4.3). |
| SQLite locked | WAL mode for concurrent reads. Single-process writes. Cron must not overlap. |
| Disk full | SQLite throws error. Logged. |
| API key invalid | First LLM call fails. Exit code 1. |
| Network down (crawl) | Per-request exception handling. Skip and continue. |
| Network down (LLM) | SDK exception. Phase returns empty. No brief that day. |


## 9. Libraries and Dependencies

### 9.1 Python Version

3.11+ (ships with Raspberry Pi OS / Ubuntu 24)

### 9.2 Required Packages

| Package | Purpose | Install |
|---|---|---|
| `anthropic` | Claude API client | `pip install anthropic --break-system-packages` |
| `requests` | HTTP for crawling + verification | `pip install requests --break-system-packages` |
| `beautifulsoup4` | HTML parsing + text extraction | `pip install beautifulsoup4 --break-system-packages` |

### 9.3 Standard Library (no install)

| Module | Purpose |
|---|---|
| `sqlite3` | Database |
| `json` | Config, response parsing, DB JSON fields |
| `hashlib` | SHA-256 content hashing |
| `re` | Date regex, JSON extraction from LLM responses |
| `difflib.SequenceMatcher` | Fuzzy quote matching |
| `unicodedata` | NFKC text normalization for quote verification |
| `html` | HTML entity decoding for text normalization |
| `logging` | File + stdout logging |
| `argparse` | CLI parsing |
| `pathlib` | Path handling |
| `time` | Rate limiting |
| `random` | Delay randomization, query shuffling, keyword weighting |
| `datetime` | Timestamps (UTC) |
| `urllib.parse` | URL encoding |

### 9.4 Optional / Future

| Package | Purpose | When |
|---|---|---|
| `apify-client` | LinkedIn scraping | If dorking insufficient (2-week eval) |
| `schedule` | Alternative to cron | If cron unreliable |
| `rich` | Terminal formatting for CLI | Nice-to-have |


## 10. Constants and Thresholds

| Constant | Value | Location |
|---|---|---|
| QUOTE_MATCH_THRESHOLD | 0.65 | phase3_verify.py |
| QUOTE_PARTIAL_THRESHOLD | 0.50 | phase3_verify.py |
| DUPLICATE_QUOTE_THRESHOLD | 0.70 | phase3_verify.py |
| DUPLICATE_WINDOW_DAYS | 7 | phase3_verify.py |
| GOOGLE_MIN_DELAY | 2.0s | phase1_crawl.py |
| GOOGLE_MAX_DELAY | 5.0s | phase1_crawl.py |
| PAGE_FETCH_DELAY | 1.0s | phase1_crawl.py |
| ALLABOLAG_RATE_LIMIT | 1.0s | phase3_verify.py |
| URL_VERIFY_TIMEOUT | 10s | phase3_verify.py |
| PAGE_FETCH_TIMEOUT | 15s | phase1_crawl.py |
| RAW_TEXT_MAX | 50,000 chars | phase1_crawl.py |
| RAW_HTML_MAX | 100,000 chars | phase1_crawl.py |
| EXTRACT_INPUT_MAX | 8,000 chars | phase2_extract.py |
| QUERIES_PER_RUN | 60 | keywords.json |
| MAX_RESULTS_PER_QUERY | 5 pages | phase1_crawl.py |
| MAX_QUERIES_PER_SITE | 15 | keywords.json |
| QUERY_COOLDOWN_DAYS | 3 | keywords.json |
| KEYWORD_RETIRE_USES | 5 | keyword_evolution.py |
| KEYWORD_RETIRE_RATE | <5% | keyword_evolution.py |
| KEYWORD_NEW_WEIGHT | 1.5x | query_builder.py |
| KEYWORD_ZERO_HIT_WEIGHT | 0.3x | query_builder.py |
| DISCOVERY_HARD_CAP | 40 | keyword_evolution.py |
| KEYWORD_INACTIVE_DAYS | 30 | keyword_evolution.py |
| SOURCE_PROMOTION_HITS | 3 | discovered_sources |
| FEEDBACK_WINDOW_DAYS | 7 | run_pipeline.py |
| SIGNALS_ANALYSIS_LIMIT | 200 | run_pipeline.py |
| SIGNALS_BRIEF_LIMIT | 100 | run_pipeline.py |
| COMPANY_CACHE_TTL_DAYS | 30 | phase3_verify.py |
| TOKEN_SOFT_CAP | 800,000 | run_pipeline.py |


## 11. Monitoring

### 11.1 Logs

- `data/logs/pipeline.log` — all phases, timestamped
- `data/logs/crawl.log` — Phase 1 detail
- `data/logs/crawl_stats_*.json` — per-run statistics

### 11.2 Health Check

```bash
sqlite3 data/intel.db "
  SELECT 'Crawled pages:',    COUNT(*) FROM raw_crawl
  UNION ALL SELECT 'Signals:', COUNT(*) FROM extracted_signals
  UNION ALL SELECT 'Verified:', COUNT(*) FROM verified_signals WHERE final_status='verified'
  UNION ALL SELECT 'Rejected:', COUNT(*) FROM verified_signals WHERE final_status='rejected'
  UNION ALL SELECT 'Runs:',    COUNT(*) FROM analysis_runs
  UNION ALL SELECT 'Feedback:', COUNT(*) FROM feedback;
"
```

### 11.3 Alert Thresholds

| Metric | Concern If |
|---|---|
| Pages crawled | <10 per run (Google blocking) |
| Signals extracted | 0 for 3+ consecutive runs |
| Verification rate | <20% (extraction quality problem) |
| Brief file | Missing (pipeline failed) |
| DB size | >500MB (no pruning, check disk) |
| Keyword changes | None for 5+ runs (stagnation) |
| Discovery keyword count | >40 (hard cap should prevent, investigate if exceeded) |
| API tokens per run | Soft circuit breaker at 800K tokens (§3.4). Per-run totals persisted in `analysis_runs`. Per-call logged in pipeline.log. Alert if 3+ consecutive runs hit the cap. |


## 12. Security

- API key: env var only, never in code/config
- No PII collection beyond publicly posted content
- SQLite: local file, no network exposure
- Allabolag data: public record (offentlighetsprincipen)
- LinkedIn: Google dorking accesses Google's cache. Apify (if added) assumes TOS risk.
- All scraping rate-limited


## 13. Not in Scope for V1

- Web dashboard for briefs/feedback
- Email/Slack notifications
- Platsbanken API integration (structured)
- Signal-to-outreach tracking
- Multi-operator support
- Database pruning/archival
- Explicit retry queue for failed extractions
- Google Alerts push integration
