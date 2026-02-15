"""
Phase 2: EXTRACT — LLM Agent 1.
Receives ONLY raw crawl data. Extracts structured signals.
Strict anti-hallucination: if it's not in the text, it doesn't exist.
"""

import json
import logging
from pathlib import Path

log = logging.getLogger("extract")

EXTRACT_SYSTEM_PROMPT = """You are a structured data extraction agent. You receive 
raw text scraped from Swedish web sources about businesses and their challenges.

YOUR ONLY JOB: Extract structured signals from the provided raw text.

ABSOLUTE RULES:
- You may ONLY extract information that is EXPLICITLY stated in the provided text
- NEVER infer, assume, or generate information not present in the text
- NEVER complete partial information with guesses
- NEVER add context from your training data about companies or people
- If a field cannot be filled from the text, use null
- Preserve original Swedish language for all quotes
- If the text contains no relevant business signals, return empty

For each business-relevant signal found, extract this exact JSON structure:

{
  "signals": [
    {
      "signal_type": "job_posting | social_post | news_mention | forum_post | company_data",
      "person": {
        "name": "full name exactly as written, or null",
        "title": "job title exactly as written, or null",
        "company": "company name exactly as written, or null"
      },
      "company": {
        "name": "company name exactly as written, or null",
        "industry": "only if explicitly stated, or null",
        "employee_count": "only if explicitly stated, or null"
      },
      "content": {
        "original_quote": "exact text from source, max 500 chars. Copy-paste, do not rewrite.",
        "topic_tags": ["relevant topic tags"],
        "expressed_problem": "what specific problem is described, in your words, or null",
        "expressed_need": "what they say they need, in your words, or null",
        "ai_awareness": "using_ai | exploring_ai | skeptical | unaware | null"
      }
    }
  ]
}

If the text contains MULTIPLE signals (e.g., an article mentioning several companies), 
extract each as a separate signal.

If the text contains NO extractable business signals, return:
{"signals": [], "reason": "brief explanation why nothing was extracted"}

CRITICAL — WHAT COUNTS AS A SIGNAL:
- A person or company describing a business problem or challenge
- A job posting revealing what a company can't do internally
- Someone expressing frustration with a process
- A company describing their experience with AI or automation
- A company describing manual/inefficient processes

WHAT IS NOT A SIGNAL:
- Generic news about AI trends with no specific company/person
- Product advertisements
- Government policy discussions without company voices
- Pure opinion pieces without concrete business examples

Respond with ONLY the JSON. No explanation, no markdown, no preamble."""


def build_extraction_prompt(source_hash: str, url: str, title: str, 
                            raw_text: str, query_used: str) -> str:
    """Build the user prompt for extraction from one crawled page."""
    
    # Truncate very long texts to manage tokens
    text = raw_text[:8000] if len(raw_text) > 8000 else raw_text
    
    return f"""SOURCE METADATA:
- URL: {url}
- Title: {title}
- Found via query: {query_used}
- Source hash: {source_hash}

RAW TEXT CONTENT:
---
{text}
---

Extract all business-relevant signals from this text. 
Remember: only extract what is explicitly stated. 
If nothing relevant, return empty signals array."""


def parse_extraction_response(response_text: str, source_hash: str) -> list:
    """
    Parse the LLM response into signal dicts.
    Handles various response formats defensively.
    """
    # Clean response
    text = response_text.strip()
    
    # Remove markdown code blocks if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON in the response
        import re
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                data = json.loads(json_match.group())
            except json.JSONDecodeError:
                log.warning(f"Could not parse extraction response for {source_hash}")
                return []
        else:
            log.warning(f"No JSON found in extraction response for {source_hash}")
            return []
    
    signals = data.get("signals", [])
    
    # Attach source_hash to each signal
    for s in signals:
        s["source_hash"] = source_hash
    
    # Basic validation
    valid = []
    for s in signals:
        # Must have at least a quote or expressed problem
        content = s.get("content", {})
        if content.get("original_quote") or content.get("expressed_problem"):
            valid.append(s)
        else:
            log.debug(f"Dropping signal without quote or problem from {source_hash}")
    
    return valid


def store_extracted_signals(conn, signals: list, model_name: str):
    """Store extracted signals in database."""
    stored = 0
    for s in signals:
        content = s.get("content", {})
        person = s.get("person", {})
        company = s.get("company", {})
        
        topic_tags = json.dumps(content.get("topic_tags", []), ensure_ascii=False)
        
        try:
            conn.execute("""
                INSERT INTO extracted_signals
                (source_hash, signal_type, person_name, person_title,
                 person_company, company_name, company_org_number,
                 company_industry, company_employee_count,
                 original_quote, expressed_problem, expressed_need,
                 ai_awareness, topic_tags, extraction_model)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s.get("source_hash"),
                s.get("signal_type"),
                person.get("name"),
                person.get("title"),
                person.get("company"),
                company.get("name"),
                company.get("org_number"),
                company.get("industry"),
                company.get("employee_count"),
                content.get("original_quote"),
                content.get("expressed_problem"),
                content.get("expressed_need"),
                content.get("ai_awareness"),
                topic_tags,
                model_name,
            ))
            stored += 1
        except Exception as e:
            log.error(f"Failed to store signal: {e}")
    
    conn.commit()
    return stored
