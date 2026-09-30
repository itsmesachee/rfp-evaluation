"""LLM client: JSON-capable evaluation agent with pluggable backend.

Backends (in precedence order):
- Runtime key: user pastes an API key in the Streamlit sidebar (e.g. OpenRouter).
  base_url points at OpenRouter's OpenAI-compatible endpoint.
- Env/secret key: OPENAI_API_KEY (+ optional OPENAI_MODEL, OPENAI_BASE_URL).
- Mock (deterministic heuristic fallback for classroom demo without API key)

The Evaluation Agent must: use only evidence present in the document,
return one result per active criterion, stay within score range, output JSON only.
"""
import json
import os
import re
from typing import List, Dict, Optional

# Runtime-configurable LLM settings (e.g. set from the Streamlit sidebar).
# These take precedence over environment variables / Streamlit secrets.
_RUNTIME_CONFIG = {"api_key": None, "model": None, "base_url": None}

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def configure(api_key: Optional[str] = None, model: Optional[str] = None,
              base_url: Optional[str] = None) -> None:
    """Set LLM credentials at runtime (e.g. from Streamlit sidebar input)."""
    if api_key is not None:
        _RUNTIME_CONFIG["api_key"] = api_key.strip() or None
    if model is not None:
        _RUNTIME_CONFIG["model"] = model.strip() or None
    if base_url is not None:
        _RUNTIME_CONFIG["base_url"] = base_url.strip() or None


def active_settings():
    """Return (api_key, model, base_url) after applying precedence rules."""
    api_key = _RUNTIME_CONFIG["api_key"] or os.environ.get("OPENAI_API_KEY")
    model = _RUNTIME_CONFIG["model"] or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    base_url = _RUNTIME_CONFIG["base_url"] or os.environ.get("OPENAI_BASE_URL")
    return api_key, model, base_url


def backend_name() -> str:
    """Human-readable label of the backend that would be used."""
    api_key, model, base_url = active_settings()
    if not api_key:
        return "mock (no API key)"
    if base_url and "openrouter" in base_url:
        return f"OpenRouter ({model})"
    return f"OpenAI ({model})"

PROMPT_TEMPLATE = """You are an RFP evaluation agent. Score ONE supplier proposal against the active criteria.

Rules:
- Use ONLY evidence present in the supplier document excerpt below. Do not invent features, prices, or certifications.
- Return one result for EVERY active criterion listed.
- Each score must be a number within 0..{max_score} inclusive (integers preferred).
- Output VALID JSON ONLY, no markdown fences, no commentary.

Active criteria (id, name, weight%%, description):
{criteria_block}

Supplier document excerpt:
\"\"\"{document}\"\"\"

Return JSON in exactly this shape:
{{
  "supplier_name": "<name>",
  "criteria": [
    {{"criterion_id": <id>, "score": <0..{max_score}>, "max_score": {max_score}, "evidence": "<short quote or paraphrase from document>", "justification": "<1-2 sentences why this score>"}}
  ],
  "risks": ["<risk 1>", "<risk 2>"],
  "overall_summary": "<2-3 sentence summary>"
}}
"""

def build_prompt(supplier_name: str, criteria: List[Dict], document_text: str, max_score: int = 10) -> str:
    block_lines = []
    for c in criteria:
        block_lines.append(f"- {c['criterion_id']}: {c['name']} ({c['weight']}%): {c['description']}")
    return PROMPT_TEMPLATE.format(
        max_score=max_score,
        criteria_block="\n".join(block_lines),
        document=document_text,
    )

def _call_openai(prompt: str, model: str = "gpt-4o-mini",
                 api_key: Optional[str] = None, base_url: Optional[str] = None) -> str:
    from openai import OpenAI
    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url  # e.g. OpenRouter's OpenAI-compatible endpoint
    client = OpenAI(**kwargs)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a precise RFP evaluator. Output valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content

# --- Mock backend: keyword-heuristic scoring for offline demo ---
CRITERION_KEYWORDS = {
    # criterion_id -> list of (keyword, weight)
    1: [("microservices", 2), ("kubernetes", 2), ("kafka", 1), ("scalability", 2), ("load test", 3), ("integration", 1), ("architecture", 2), ("api", 1)],
    2: [("milestone", 2), ("gantt", 2), ("risk register", 3), ("staffing", 2), ("timeline", 1), ("phase", 1), ("contingency", 2), ("raci", 2)],
    3: [("price", 1), ("cost", 1), ("tco", 2), ("assumption", 2), ("fixed fee", 2), ("pricing clarity", 2), ("discount", 1)],
    4: [("iso 27001", 3), ("soc 2", 3), ("encryption", 2), ("pen test", 2), ("gdpr", 2), ("audit", 2), ("mfa", 1), ("dpa", 2)],
    5: [("24/7", 2), ("sla", 2), ("reference", 2), ("csat", 2), ("support", 1), ("training", 1), ("hypercare", 1)],
}

NEGATIVE_SIGNALS = {
    1: ["vague", "no load-test", "not provided", "roadmap item"],
    2: ["brief", "generic"],
    4: ["limited", "not documented", "no iso", "weak compliance"],
    5: ["no prior", "limited experience"],
}

def _mock_score(document_text: str, criteria: List[Dict]) -> Dict:
    text = document_text.lower()
    criteria_out = []
    for c in criteria:
        cid = c["criterion_id"]
        kws = CRITERION_KEYWORDS.get(cid, [])
        hits = sum(w for kw, w in kws if kw in text)
        # base 4 + hits scaled, capped
        score = 4 + min(hits, 10) * 0.5
        # penalize negative signals
        for neg in NEGATIVE_SIGNALS.get(cid, []):
            if neg in text:
                score -= 0.75
        # small deterministic variation by supplier name hash to avoid ties
        score = max(2, min(10, round(score)))
        # extract a short evidence snippet: first sentence containing a keyword
        evidence = "General proposal content."
        for kw, _ in kws:
            idx = text.find(kw)
            if idx != -1:
                start = max(0, text.rfind(".", 0, idx) + 1)
                end = text.find(".", idx)
                snippet = document_text[start:end+1].strip() if end != -1 else document_text[start:start+160]
                if snippet:
                    evidence = snippet[:220]
                break
        criteria_out.append({
            "criterion_id": cid,
            "score": score,
            "max_score": c.get("max_score", 10),
            "evidence": evidence,
            "justification": f"Mock heuristic: {hits} positive keyword hits for '{c['name']}'. Score reflects evidence density in document.",
        })
    risks = []
    if "risk" not in text:
        risks.append("Risk plan detail not clearly evidenced in document.")
    else:
        risks.append("Integration dependencies noted; mitigation quality varies by supplier.")
    if "sap" in text and ("vague" in text or "roadmap" in text):
        risks.append("SAP integration approach lacks concrete detail.")
    return {
        "supplier_name": "supplier",
        "criteria": criteria_out,
        "risks": risks[:3],
        "overall_summary": "Mock evaluation (no LLM API key configured). Scores derived from keyword evidence density; connect an LLM for nuanced judgment.",
    }

def evaluate_supplier(supplier_name: str, criteria: List[Dict], document_text: str) -> Dict:
    """Call the configured LLM backend and return parsed JSON dict (raw, unvalidated)."""
    from .document_tool import truncate_for_prompt
    short_doc = truncate_for_prompt(document_text)
    max_score = criteria[0].get("max_score", 10) if criteria else 10
    prompt = build_prompt(supplier_name, criteria, short_doc, max_score)
    api_key, model, base_url = active_settings()
    if api_key:
        raw = _call_openai(prompt, model, api_key, base_url)
    else:
        mocked = _mock_score(document_text, criteria)
        mocked["supplier_name"] = supplier_name
        return mocked
    # try to parse JSON robustly
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise ValueError(f"LLM did not return valid JSON: {raw[:500]}")
