"""
Phase 4: ANALYZE — LLM Agent 2
Phase 5: BRIEF — LLM Agent 3

Both are LLM-driven. Prompts defined here, calls made by pipeline.
"""

# ============================================================
# PHASE 4: ANALYSIS
# ============================================================

ANALYZE_SYSTEM_PROMPT = """You are a market analysis agent studying the Swedish 
small business (SMB) sector to find underserved problems and business opportunities.

You receive ONLY verified, source-checked signals. Every signal has been confirmed 
to exist at its stated source URL with its stated quote.

YOUR JOB: Find patterns, clusters, and white spaces — problems that businesses 
have but nobody is solving well.

PRODUCE THIS EXACT JSON STRUCTURE:

{
  "problem_clusters": [
    {
      "name": "short name for this problem cluster",
      "description": "what the cluster represents",
      "signal_count": 0,
      "signal_ids": [],
      "intensity": "high | medium | low",
      "trend": "growing | stable | shrinking | new",
      "example_quotes": ["1-2 strongest quotes from signals"]
    }
  ],
  "white_spaces": [
    {
      "problem": "a problem mentioned but with no visible solution provider",
      "signal_ids": [],
      "opportunity_description": "why this is an opportunity",
      "estimated_demand": "high | medium | low | unknown"
    }
  ],
  "watchlist_companies": [
    {
      "company_name": "name",
      "signal_count": 0,
      "signal_ids": [],
      "summary": "what we know about their situation",
      "org_number": "if available",
      "employee_count": "if available"
    }
  ],
  "sector_patterns": [
    {
      "sector": "sector name",
      "signal_count": 0,
      "dominant_problems": ["list of problems"],
      "ai_readiness": "high | medium | low"
    }
  ],
  "discovery_suggestions": [
    {
      "source": "URL or description of where to look",
      "reason": "why this might yield good signals"
    }
  ]
}

RULES:
- Every claim must reference specific signal IDs
- Do not add knowledge beyond what's in the signals
- If a pattern is based on fewer than 3 signals, mark intensity as "low" 
  and add "weak_signal": true
- Prioritize items tagged "more" in feedback, deprioritize "less" items
- Be blunt. No filler. If there's nothing interesting, say so.
- Output ONLY the JSON. No markdown, no explanation."""


def build_analysis_prompt(verified_signals: list, focus_config: str, 
                          feedback: list, previous_analysis: dict = None) -> str:
    """Build the user prompt for analysis."""
    
    # Format signals
    signals_text = ""
    for i, s in enumerate(verified_signals):
        signals_text += f"\n[Signal {s['id']}]\n"
        if s.get("person_name"):
            signals_text += f"  Person: {s['person_name']}"
            if s.get("person_title"):
                signals_text += f" ({s['person_title']})"
            signals_text += "\n"
        if s.get("company_name"):
            signals_text += f"  Company: {s['company_name']}"
            if s.get("company_industry"):
                signals_text += f" [{s['company_industry']}]"
            if s.get("company_employee_count"):
                signals_text += f" ({s['company_employee_count']} employees)"
            signals_text += "\n"
        if s.get("original_quote"):
            signals_text += f'  Quote: "{s["original_quote"][:300]}"\n'
        if s.get("expressed_problem"):
            signals_text += f"  Problem: {s['expressed_problem']}\n"
        if s.get("expressed_need"):
            signals_text += f"  Need: {s['expressed_need']}\n"
        if s.get("ai_awareness"):
            signals_text += f"  AI awareness: {s['ai_awareness']}\n"
        signals_text += f"  Source: {s.get('source_url', 'unknown')}\n"
    
    # Format feedback
    feedback_text = ""
    if feedback:
        more = [f for f in feedback if f.get("rating") == "more"]
        less = [f for f in feedback if f.get("rating") == "less"]
        if more:
            feedback_text += "Items marked 'MORE LIKE THIS':\n"
            for f in more:
                feedback_text += f"  - Signal {f.get('signal_id')}: {f.get('note', '')}\n"
        if less:
            feedback_text += "Items marked 'LESS LIKE THIS':\n"
            for f in less:
                feedback_text += f"  - Signal {f.get('signal_id')}: {f.get('note', '')}\n"
    
    # Previous analysis summary for trend detection
    prev_text = ""
    if previous_analysis:
        clusters = previous_analysis.get("problem_clusters", [])
        if clusters:
            prev_text = "PREVIOUS RUN'S TOP CLUSTERS (for trend comparison):\n"
            for c in clusters[:5]:
                prev_text += f"  - {c['name']}: {c['signal_count']} signals\n"
    
    return f"""CURRENT FOCUS:
{focus_config}

{f"USER FEEDBACK:{chr(10)}{feedback_text}" if feedback_text else "No feedback yet."}

{prev_text}

VERIFIED SIGNALS ({len(verified_signals)} total):
{signals_text}

Analyze these signals. Find patterns, white spaces, and opportunities.
Output JSON only."""


# ============================================================
# PHASE 5: BRIEF
# ============================================================

BRIEF_SYSTEM_PROMPT = """You are a brief writer producing a daily intelligence 
report for a solo consultant looking for business opportunities in Swedish SMBs.

You receive verified analysis and verified signals. Your job is to write a 
concise, actionable brief.

EVERY brief follows this EXACT format:

# SMB Intelligence Brief — [date]
## Current Focus: [1-line summary of focus file]

### 🔴 Top Signals
[3-5 most important findings. Each MUST include:]
- **What**: one sentence
- **Who**: full name, title, company (or "Anonymous" if unavailable)
- **Source**: [clickable URL]
- **Quote**: "exact quote in Swedish"
- **Why it matters**: one sentence connecting to opportunity

### 📊 Problem Clusters
[Ranked list with signal count and trend]
1. **[Cluster name]** — X signals [↑↓→] — [one line description]

### ⬜ White Spaces
[Problems nobody is solving. Each with:]
- Problem: [what]
- Evidence: [how many signals, from which sectors]
- Opportunity: [what you could offer]

### 🏢 Watchlist
[Companies with 2+ signals]
| Company | Employees | Industry | Signals | Key Issue |
|---------|-----------|----------|---------|-----------|

### 🔍 Weak Signals
[Interesting but needs more data]

### 🆕 New This Run
[Anything that appeared for the first time]

---
**Action items**: [1-3 concrete things to do based on this brief]

RULES:
- EVERY person mention: name, title, company. No exceptions.
- EVERY claim: source URL and date. No exceptions.
- If you can't cite it, exclude it.
- Quotes stay in Swedish.
- Rest in English.
- Be blunt. No padding. If today was boring, say so.
- Max length: 1500 words."""


def build_brief_prompt(analysis: dict, signals: list, run_date: str,
                       focus_summary: str) -> str:
    """Build the user prompt for brief generation."""
    
    return f"""RUN DATE: {run_date}
FOCUS: {focus_summary}

ANALYSIS RESULTS:
{json.dumps(analysis, ensure_ascii=False, indent=2)}

VERIFIED SIGNALS FOR CITATION:
{json.dumps([{
    "id": s["id"],
    "person_name": s.get("person_name"),
    "person_title": s.get("person_title"),
    "company_name": s.get("company_name"),
    "original_quote": s.get("original_quote"),
    "source_url": s.get("source_url"),
    "expressed_problem": s.get("expressed_problem"),
} for s in signals], ensure_ascii=False, indent=2)}

Write the daily brief. Every claim must cite signal IDs and source URLs."""


import json  # needed for build_brief_prompt
