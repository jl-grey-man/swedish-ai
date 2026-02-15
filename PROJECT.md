# SMB Intelligence System

## 1. What This Is

An autonomous research system that monitors the Swedish small business landscape to find companies actively struggling with problems that AI automation can solve. It runs daily on a Raspberry Pi 5, crawls public Swedish-language sources, extracts verified intelligence signals, and delivers a structured brief identifying specific companies, their stated problems, and market gaps where no solution provider exists.

This is not a generic "AI trends tracker." It finds a real person, at a real company, describing a real problem, and surfaces that as a potential consulting lead.

Output example of what "done" looks like: *"Anna Andersson, HR officer at a cleaning supplies agent in Malmö, posted on LinkedIn yesterday that her 12-person company spends 3 hours daily copying order data between systems."* — That is a signal. A name, a company, a problem, a source, a date. Everything verifiable.


## 2. Why It Exists

### 2.1 The Market Opportunity

Tillväxtverket's 2025 report on Swedish SMB AI competence (Rapport 0508, authored by PA Consulting Group) found a structural gap in the Swedish consulting market:

> "Marknaden i dag saknar förmåga att möta SMF när det gäller att utveckla och implementera rätt lösningar på företagsspecifika problem."

Translation: The consulting market currently lacks the ability to meet SMBs when it comes to developing and implementing the right solutions for company-specific problems.

Supporting data:

- 74.7% of Swedish companies that considered AI but didn't adopt it cited **lack of expertise** as the primary barrier (SCB, 2024).
- 41.7% of AI-using Swedish companies apply it to marketing and sales — the most common use case (SCB).
- Swedish SMBs use AI more than many comparable countries, but utilization is far below potential.
- Companies that tried consulting found consultants didn't understand small-company operations and couldn't deliver enough value within affordable consultant-hours.

The demand exists. The gap is not "do SMBs need AI help" — it's "which specific SMBs are ready, and what exact problems do they need solved."

### 2.2 Evidence Base — What Swedish SMBs Actually Say

The system design is informed by six real case studies from the Tillväxtverket report. These are not hypothetical personas — they are documented interviews with real Swedish companies. The system is designed to find more companies like these, at scale, automatically.

**Case 1: Auto Parts Subcontractor (~20 employees)**
High admin workload, multilingual customer communication needs, inventory optimization. Implemented AI for text production (success), demand forecasting (failed — never reliable), internal knowledge management (exploring). Key finding: struggled to find consultants who understand small business operations. Government support helped but didn't cover enough consultant hours.

**Case 2: Packaging Manufacturer (~200 employees)**
Manual order handling, production planning, quality control — slow and error-prone. Implemented AI for automated order reading (saves 3–5 hours/week), safety datasheet processing, and image-based production validation. Measurable efficiency gains achieved.

**Case 3: Design Company (2 employees, exports to Europe)**
Multilingual customer communication overwhelming two-person team. Content production consuming all available time. Admin tasks (quotes, CRM) unmanageable. Implemented AI for product texts, website copy, social media in multiple languages, connected to e-commerce and CRM. Frustration: can't find AI tools for visual marketing. Government support programs don't target companies this small. Consultant costs prohibitive.

**Case 4: Industrial Metalworks (26 employees)**
Barely started. Identified potential in production data analysis, furnace optimization, production planning. Reality: only used ChatGPT for internal documents. Barriers: no internal competence, **"don't know where to turn for qualified advice"**, conservative company culture, equipment suppliers slow to digitalize.

**Case 5: Circular Commerce Platform (4 employees, startup)**
Product data from multiple suppliers varies wildly in quality and structure. Manual review bottleneck killing growth. Implemented AI to standardize descriptions, correct errors, optimize for SEO. Key finding: AI project took 1 month to build; the government grant application took 6 months.

**Case 6: Architecture Firm (~40 employees)**
Explored but not implemented. Tested image generation, parametric design, press release tools. Found AI too immature for creative architecture work. Stated need: **"Concrete examples from someone who has actually implemented similar solutions"** in their industry, to see what's actually possible before investing.

### 2.3 The Pattern

None of these companies said "I need AI." They said:

- "Order handling takes too many hours"
- "Can't write marketing content in 5 languages with 2 people"
- "Product data is a mess and it's slowing our growth"
- "Don't know where to turn for help"
- "Want to see a real example before investing"

The system is built to detect this kind of language — problem language, not AI language.

### 2.4 The Operator's Problem

The operator is a solo consultant entering the AI automation consulting market in Sweden. Background in marketing, sales, and AI/LLM systems. No existing client network or pipeline. Cold outreach to random SMBs would be low-yield guesswork. This system replaces guesswork with evidence: it finds companies already expressing pain publicly, so outreach can be relevant and specific.

### 2.5 Additional Market Intelligence

From Almega (Swedish service company association): Companies use AI primarily for summarizing data, processing large text volumes, making presentations, writing proposals (anbud), and documenting meetings. The consistent pattern: companies use AI to free staff from admin work so they can focus on core business.

From Teknikministeriet (Feb 2026): Companies know they should publish content but get stuck in the research/structure/writing phase. The gap between idea and published text feels insurmountable — a content production bottleneck across Swedish SMBs.

From concrete international case studies (applicable patterns): nightly RFM analysis to detect at-risk customers and trigger retention campaigns; AI agents that qualify website prospects and book meetings into calendars outside business hours; automated transcription and summarization of client interviews saving consultant time.


## 3. Success Criteria

**Week 1–2:** System crawls and extracts signals. Briefs may be sparse. Keyword evolution begins learning. This phase is expected to be noisy — not a failure.

**Week 3–4:** Briefs contain at least 3–5 actionable leads per week. "Actionable" means: a real company, a verifiable problem, enough context for relevant outreach. Keyword vocabulary has expanded from signal language.

**Day 90:** System consistently surfaces high-value signals. Discovery keywords and sources have self-tuned through feedback. The operator has used briefs to make informed, targeted outreach — not to accumulate more research.

**Hard constraint:** This system must lead to client conversations within 30 days. It is a prospecting tool, not an intellectual exercise. If it becomes a substitute for outreach rather than a support for it, it has failed.


## 4. Core Design Principles

### 4.1 Hallucination-Proof by Architecture

The single most important design constraint. Every claim in every brief must trace back to a verified source with a working URL and an exact quote. This is enforced structurally — not by prompting alone.

The rule: **LLMs never touch the internet. Scrapers never analyze.** Complete separation between data collection (deterministic, no AI) and data interpretation (AI on verified local data only).

If a signal cannot be cited — exact person, exact company, exact quote, working URL — it does not appear in the brief. No "one person on LinkedIn said..." — it must be "Anna Andersson, HR officer at Städprodukter AB, posted on LinkedIn on Feb 14..."

### 4.2 The 66/34 Exploration Split

Both sources and keywords follow a 66% exploitation / 34% exploration split. This ratio applies everywhere:

**Sources:** 66% predetermined (Platsbanken, LinkedIn via dorking, news sites, forums), 34% discovered by following threads from fixed sources. Discovery sources earn their place: 3+ good signal hits and they graduate to the fixed list.

**Keywords:** 66% core pain/need terms (known Swedish business vocabulary), 34% discovery terms derived from the actual language verified signals use. The system learns what words real business owners use to describe their problems.

**The rationale:** Searching only for "AI" and "automatisering" misses the best signals. Someone posting "vi lägger 3 timmar om dagen på att kopiera data mellan system" is a better lead than someone posting "AI is the future." The 34% discovery layer catches the vocabulary you couldn't predict. If verified signals use the word "drunknar" to describe admin overload, "drunknar" becomes a discovery keyword — not because it was predicted, but because a real person used it.

Discovery keywords and sources are not random. They are adjacent — suggested by an LLM that has read the actual verified signals and proposes vocabulary it found in them. Underperforming keywords (used 5+ times, hit rate below 5%) get retired automatically.

### 4.3 What Counts as a Signal

A signal is a specific instance of a person or company expressing a business problem, need, or AI-related experience. Five signal types:

**Job postings:** A company hiring for a role that AI could partially or fully automate. A warehouse company hiring a "data entry clerk" reveals they can't do something internally.

**Social posts:** A business owner on LinkedIn describing frustration with a process. A CEO posting about spending weekends on invoicing.

**News mentions:** A Breakit article quoting a manufacturer about production planning challenges.

**Forum posts:** A Flashback thread where someone asks how to automate order handling.

**Company data:** Allabolag enrichment revealing company size, revenue, and industry — context for viability assessment.

**What is NOT a signal:** Generic AI trend articles without company voices. Product advertisements. Government policy discussions without business owner quotes. Opinion pieces without concrete business examples.

### 4.4 The Focus File

A plain-text configuration file the operator edits directly. Defines priority sectors, priority problems, company size targets, and ignore lists. Changes take effect on the next run. This is the strategic rudder — the system is autonomous but not unsupervised.

Current defaults: priority on e-commerce, professional services, manufacturing, retail. Target company size 2–50 employees. Ignoring healthcare, public sector, enterprise (250+), and AI startups (they're not the customer).

### 4.5 The Feedback Loop

After reading each brief, the operator marks individual signals as "more like this" or "less like this" via a CLI tool. This feedback is stored in the database and injected into the analysis phase (Phase 4), gradually teaching the system what's valuable. The keyword evolution module (Phase 6) also reads feedback when deciding which discovery terms to prioritize or retire.

Minimum viable feedback: 3–5 ratings per brief. Without feedback, the exploration component operates blind.


## 5. The Six-Phase Pipeline

Each phase has one job, one input, one output. Phases execute sequentially. LLM-powered phases are sandboxed: they receive only the output of the previous phase, never raw internet access.

```
[keywords.json + focus.txt]
         │
         ▼
  ┌──────────────┐
  │  PHASE 1:    │  No LLM. Google dorking, page fetching.
  │  CRAWL       │  Stores raw text + HTML + URLs.
  └──────┬───────┘
         │ raw_crawl table
         ▼
  ┌──────────────┐
  │  PHASE 2:    │  LLM Agent 1. Extracts structured data
  │  EXTRACT     │  from raw text. One page per call.
  └──────┬───────┘
         │ extracted_signals table
         ▼
  ┌──────────────┐
  │  PHASE 3:    │  No LLM. Quote check, URL check,
  │  VERIFY      │  Allabolag lookup, dedup.
  └──────┬───────┘
         │ verified_signals table
         ▼
  ┌──────────────┐
  │  PHASE 4:    │  LLM Agent 2. Pattern detection,
  │  ANALYZE     │  clustering, white space identification.
  └──────┬───────┘
         │ analysis_runs table
         ▼
  ┌──────────────┐
  │  PHASE 5:    │  LLM Agent 3. Writes structured
  │  BRIEF       │  markdown brief with full citations.
  └──────┬───────┘
         │ briefs/brief_YYYY-MM-DD.md
         ▼
  ┌──────────────┐
  │  PHASE 6:    │  LLM Agent 4. Suggests new keywords,
  │  EVOLVE      │  retires underperformers.
  └──────┬───────┘
         │ updated keywords.json
         ▼
   [Next day's crawl]
```

### Phase 1: CRAWL (No LLM — Deterministic)

Generates search queries from keyword config (66/34 split), executes them as Google dork searches against site targets, fetches result pages, stores everything in SQLite. Every item gets a SHA-256 content hash, exact URL, raw HTML, extracted text, and UTC timestamp.

Rate limiting: 2–5 second randomized delay between Google queries. 1 second between page fetches. 3-day cooldown before query reuse. Max 5 result pages fetched per query. User agent rotation. robots.txt respected. CAPTCHA detection: if 20 consecutive queries return 0 results, pause 60 seconds.

Input: `keywords.json`, `focus.txt`
Output: Rows in `raw_crawl` table

### Phase 2: EXTRACT (LLM Agent 1)

Processes each unextracted crawl result through an LLM with strict anti-hallucination instructions. The agent may ONLY extract information explicitly present in the provided text. Extracts: person name, title, company, exact quote (copy-paste, not rewritten), expressed problem, expressed need, AI awareness level. Missing fields = null, never guessed.

One page per LLM call. Structured JSON output. Stored with foreign key to raw crawl source.

Input: Raw crawl data (one page at a time)
Output: Rows in `extracted_signals`

### Phase 3: VERIFY (No LLM — Deterministic)

Four checks per signal:

1. **Quote check:** Fuzzy-match extracted quote against original raw text. Sliding window with 65% similarity threshold. Also checks first/second half independently for partial matches. Fail → rejected.
2. **URL check:** HTTP HEAD request to source URL. Dead → rejected. Redirect or restricted (403/401) → still live.
3. **Company check:** Allabolag.se lookup if company name present. Enriches with org number, employee count, industry code. Results cached (30-day TTL) to avoid redundant lookups. Not found → flagged, not rejected.
4. **Dedup check:** Same person + company + similar quote (>70% similarity) within 7 days → merged.

Output statuses: "verified" (all pass), "weak" (partial pass), "rejected" (excluded from downstream).

Input: `extracted_signals` + `raw_crawl` tables
Output: Rows in `verified_signals`

### Phase 4: ANALYZE (LLM Agent 2)

Receives only verified signals, focus file, user feedback, and previous analysis (for trend detection). Produces structured JSON containing:

- **Problem clusters:** Grouped signals, ranked by frequency/intensity, with trend vs. previous run
- **White spaces:** Problems with no visible solution provider
- **Watchlist companies:** Companies with 2+ signals
- **Sector patterns:** Industry breakdown with AI readiness
- **Discovery suggestions:** New sources based on signal content

Every claim references specific signal IDs. Patterns on <3 signals flagged as "weak signal."

Input: Verified signals, focus file, feedback, previous analysis
Output: Row in `analysis_runs` (JSON fields)

### Phase 5: BRIEF (LLM Agent 3)

Takes analysis + verified signals, writes daily markdown brief. Fixed structure, no variation:

1. Top Signals (3–5, each with: what, who [name/title/company], quote in Swedish, source URL, why it matters)
2. Problem Clusters (ranked, trend arrows, signal counts)
3. White Spaces (problem, evidence, opportunity)
4. Watchlist (table: company, employees, industry, signals, key issue)
5. Weak Signals (worth watching)
6. New This Run (first appearances)
7. Action Items (1–3 concrete next steps)

Anything uncitable → excluded. Max ~1500 words.

Input: Analysis JSON, verified signals, focus summary
Output: `briefs/brief_YYYY-MM-DD.md`

### Phase 6: KEYWORD EVOLUTION (LLM Agent 4)

Reviews verified signals, suggests 5–15 new discovery keywords from actual signal language. Identifies underperforming keywords (5+ uses, <5% hit rate) for retirement. Updates `keywords.json` (with backup). Tracks all keywords in `keyword_history` table for performance measurement.

Input: Recent verified signals, current keywords, keyword performance stats
Output: Updated `keywords.json`, rows in `keyword_history`


## 6. Data Sources

### 6.1 Fixed Sources (66%)

| Source | What It Provides | Access Method |
|---|---|---|
| Platsbanken (Arbetsförmedlingen) | Job listings revealing internal capability gaps | API / scraping with company size filters |
| LinkedIn public posts | Business owners describing problems | Google dorking (`site:linkedin.com/posts`) |
| LinkedIn articles | Longer thought pieces on business challenges | Google dorking (`site:linkedin.com/pulse`) |
| Breakit.se | Swedish tech/business news with company quotes | RSS / search scraping |
| Di.se (Dagens Industri) | Business news, SMB coverage | RSS / search scraping |
| Ny Teknik | Technology adoption stories | RSS / search scraping |
| Företagarna.se | SMB member stories, articles, advocacy | Search scraping |
| Flashback.org (f235) | Business/entrepreneurship forum threads | Search scraping |
| Reddit r/sweden, r/företagande | Community discussions | Search scraping |
| Allabolag.se | Company verification/enrichment (not a crawl source) | Triggered by company names found elsewhere |
| General Swedish sites | Catch-all for .se domain content | Google dorking (`site:.se`) |

### 6.2 Discovery Sources (34%)

Not predefined. Discovered by following threads from fixed source results. A Breakit article quoting a CEO → check their LinkedIn, company career page, company blog. A forum post mentioning a company → Allabolag lookup for size/industry, then check career page. Sources producing 3+ verified signals auto-promote to fixed list.

### 6.3 LinkedIn Strategy

**Phase 1 (launch):** Google dorking only. `site:linkedin.com/posts "keyword"`. Free, legal, covers ~60% of public posts.

**Phase 2 (if needed, 2-week evaluation):** Add Apify LinkedIn scrapers (~$50/month). Pre-built, proxy-handled, gray area but risk sits with Apify.

**Not viable:** LinkedIn API (only shows own profile + connections without marketing partner registration).


## 7. Keyword Strategy

### 7.1 Core Keywords (66%)

Four categories combined into search queries:

**Pain signals:** manuellt · tar för lång tid · tidskrävande · ineffektivt · repetitivt · flaskhals · hinner inte · överbelastade · administrativ börda · kostar för mycket tid · fel i · missar kunder · tappar kunder · svårt att hitta personal · brist på kompetens

**AI awareness:** AI · artificiell intelligens · ChatGPT · automatisering · digitalisering · maskininlärning

**Business context:** småföretag · SMF · egenföretagare · företagare · litet företag · e-handel · konsultbolag · byrå · tillverkning

**Specific tasks:** orderhantering · fakturering · kundservice · marknadsföring · sociala medier · content · leadgenerering · CRM · bokföring · offerthantering · lagerstyrning · produktbeskrivningar · översättning

### 7.2 Discovery Keywords (34%)

Seed list: drunknar i · önskar att · behöver hjälp med · frustrerad · omöjligt att hinna · pappersarbete · dubbelarbete · copy paste · excel helvete · mötesanteckningar · kundklagomål · onboarding · säljprocess

After each run, keyword evolution (Phase 6) adds terms from verified signals and retires underperformers. New keywords get 1.5x selection weight. Proven keywords get weighted by hit rate. Zero-hit keywords (after 5 uses) drop to 0.3x weight, then retire. Hard cap: 40 active discovery keywords maximum. Keywords unused for 30+ days are retired regardless of hit rate — if they're not being sampled often enough to evaluate, they're consuming space. When at cap, new keywords evict the least-recently-used, lowest-performing existing keyword.

### 7.3 Query Construction

Templates: `{site} "{pain}" "{context}"` · `{site} "{task}" "{pain}"` · `{site} "{ai}" "{context}" "{pain}"` · `{site} "{discovery}" "{context}"`

60 queries per run. Max 15 per site. 3-day reuse cooldown.


## 8. Guardrails

### 8.1 Must Never

- Present LLM-generated claims as verified signals
- Include unverified signals in briefs
- Fabricate or embellish quotes
- Guess at names, companies, or titles
- Give LLM agents internet access during Phases 4–6
- Skip Phase 3 (verification) under any circumstance

### 8.2 May

- Flag "weak" signals separately from "verified"
- Suggest sources and keywords autonomously
- Auto-promote discovery sources (3+ hits)
- Retire underperforming keywords
- Produce sparse or empty briefs — honest is better than fabricated

### 8.3 Operator Override

Nothing requires approval. System runs on cron. Operator steers via focus file edits, keyword config edits, and feedback ratings. All configuration is plain text, human-readable.


## 9. Deployment

**Hardware:** Raspberry Pi 5, 8GB RAM, headless, always-on home server (already operational).

**Schedule:** Daily via cron. Recommended: early morning (lowest Google rate-limit risk).

**LLM:** Claude API, Sonnet model (cost/quality balance).

**Cost:** $2–5/day. ~$60–150/month. LLMs only process pre-filtered verified text, not raw pages.

**Storage:** SQLite single file. ~10–50 MB/month growth.


## 10. What This System Is Not

Not a CRM (no relationship tracking). Not a lead scorer (no conversion ranking). Not a marketing tool (no outreach generation). Not a company database (no comprehensive registry).

It is a research and prospecting tool. It finds evidence. What the operator does with that evidence is outside scope.


## 11. Assumptions and Risks

### 11.1 Assumptions

- Swedish SMBs express problems publicly often enough for useful signal volume
- Google indexes ~60% of public LinkedIn posts
- Operator provides 3–5 feedback ratings per brief
- Claude API pricing remains stable
- The consulting market gap identified in 2025 persists

### 11.2 Risks

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Google rate limiting | Crawl fails | Medium | Randomized delays, UA rotation, cooldown, pause on detection |
| Source HTML changes | Scrapers break silently | Medium | Verification catches dead data; monitor crawl stats |
| Low initial signal volume | Sparse briefs weeks 1–2 | High | Expected and acceptable. Keyword evolution needs ramp time. |
| LinkedIn yield insufficient | Missing key source | Medium | 2-week evaluation gate, Apify fallback |
| Allabolag scraping limits | Enrichment fails | Low | Rate-limited; company cache (30-day TTL) reduces requests; enrichment is additive, not blocking |
| System becomes procrastination | No client conversations | Medium | Hard 30-day constraint: must produce outreach, not just research |
| Keyword drift | Discovery terms wander | Low | Feedback + performance retirement keeps focus |


## 12. Open Questions

- Google News Alerts (push) in addition to active search (pull)?
- Platsbanken official API vs. scraping — which gives richer data?
- Brief delivery: email/notification on new brief, or just file on disk?
- English-language signals from Swedish companies/domains?
- Should system track which signals led to actual outreach and outcomes?
