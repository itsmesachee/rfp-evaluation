"""Validation Tool: checks schema, fills missing criteria, clips invalid scores, records warnings."""
from typing import List, Dict, Tuple

def validate_llm_result(raw: Dict, criteria: List[Dict]) -> Tuple[Dict, List[str]]:
    """
    Returns (normalized_result, warnings).
    Normalized result shape:
    {
      "supplier_name": str,
      "criteria": [{"criterion_id": int, "name": str, "score": float, "max_score": int,
                    "weight": float, "evidence": str, "justification": str}],
      "risks": [str],
      "overall_summary": str
    }
    """
    warnings = []
    if not isinstance(raw, dict):
        raise ValueError("LLM result must be a JSON object")

    supplier_name = str(raw.get("supplier_name", "unknown"))
    active_ids = {c["criterion_id"]: c for c in criteria}

    raw_criteria = raw.get("criteria", [])
    if not isinstance(raw_criteria, list):
        warnings.append("'criteria' was not a list; resetting to empty and filling defaults.")
        raw_criteria = []

    by_id = {}
    for entry in raw_criteria:
        if not isinstance(entry, dict):
            warnings.append(f"Ignoring malformed criterion entry: {entry!r}")
            continue
        cid = entry.get("criterion_id")
        try:
            cid = int(cid)
        except (TypeError, ValueError):
            warnings.append(f"Ignoring entry with invalid criterion_id: {entry!r}")
            continue
        if cid not in active_ids:
            warnings.append(f"Ignoring unknown criterion_id {cid}.")
            continue
        if cid in by_id:
            warnings.append(f"Duplicate criterion_id {cid}; keeping first.")
            continue
        by_id[cid] = entry

    normalized_criteria = []
    for cid, c in active_ids.items():
        max_score = int(c.get("max_score", 10))
        if cid not in by_id:
            warnings.append(f"Missing criterion '{c['name']}' (id {cid}); filled with score 0.")
            normalized_criteria.append({
                "criterion_id": cid, "name": c["name"], "score": 0.0, "max_score": max_score,
                "weight": float(c["weight"]), "evidence": "", "justification": "No LLM result; defaulted to 0.",
            })
            continue
        e = by_id[cid]
        # score
        raw_score = e.get("score", 0)
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            warnings.append(f"Criterion '{c['name']}': non-numeric score {raw_score!r}; defaulted to 0.")
            score = 0.0
        if score < 0 or score > max_score:
            clipped = max(0.0, min(float(max_score), score))
            warnings.append(f"Criterion '{c['name']}': score {score} out of range [0,{max_score}]; clipped to {clipped}.")
            score = clipped
        # max_score mismatch
        e_max = e.get("max_score", max_score)
        try:
            e_max = int(e_max)
        except (TypeError, ValueError):
            e_max = max_score
        if e_max != max_score:
            warnings.append(f"Criterion '{c['name']}': LLM max_score {e_max} != configured {max_score}; using configured.")
        evidence = str(e.get("evidence", "") or "")[:1000]
        justification = str(e.get("justification", "") or "")[:1000]
        if not evidence:
            warnings.append(f"Criterion '{c['name']}': empty evidence.")
        normalized_criteria.append({
            "criterion_id": cid, "name": c["name"], "score": score, "max_score": max_score,
            "weight": float(c["weight"]), "evidence": evidence, "justification": justification,
        })

    risks = raw.get("risks", [])
    if not isinstance(risks, list):
        warnings.append("'risks' was not a list; reset to empty.")
        risks = []
    risks = [str(r)[:500] for r in risks if isinstance(r, (str, int, float))][:5]

    summary = str(raw.get("overall_summary", "") or "")[:2000]

    normalized = {
        "supplier_name": supplier_name,
        "criteria": sorted(normalized_criteria, key=lambda x: x["criterion_id"]),
        "risks": risks,
        "overall_summary": summary,
    }
    return normalized, warnings
