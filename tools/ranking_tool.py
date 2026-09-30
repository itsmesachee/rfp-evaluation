"""Ranking Tool: deterministic Python only. No LLM involved.

Formulas:
- absolute weighted score = sum((score / max_score) * weight)
- benchmark per criterion = max valid score observed
- gap = supplier score - benchmark (<=0)
- relative % = (supplier score / benchmark) * 100 ; if benchmark == 0 -> 100.0
- PPI = weighted average of relative % = sum(relative * weight) / sum(weights)

Tie-break order (stable sort):
1) higher PPI -> 2) earlier submission_date -> 3) higher experience_rating -> 4) supplier name asc
Then assign sequential ranks 1..N.
"""
from typing import List, Dict
from datetime import datetime

def _parse_date(s: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    # fallback: treat as far future so it sorts last
    return datetime.max

def compute_scores_and_ranking(suppliers: List[Dict], criteria: List[Dict]) -> Dict:
    """
    suppliers: list of {
        "supplier_name": str, "submission_date": str (YYYY-MM-DD),
        "experience_rating": float, "validated": normalized LLM result,
        "warnings": [str]
    }
    Returns dict with per-supplier metrics and leaderboard order.
    """
    weights = {c["criterion_id"]: float(c["weight"]) for c in criteria}
    total_weight = sum(weights.values()) or 100.0

    # 1. absolute scores
    for s in suppliers:
        abs_score = 0.0
        for cr in s["validated"]["criteria"]:
            cid = cr["criterion_id"]
            ms = cr["max_score"] or 10
            abs_score += (cr["score"] / ms) * weights.get(cid, 0.0)
        s["absolute_score"] = round(abs_score, 2)

    # 2. benchmarks per criterion
    benchmarks = {}
    for c in criteria:
        cid = c["criterion_id"]
        scores = [next(cr["score"] for cr in s["validated"]["criteria"] if cr["criterion_id"] == cid)
                  for s in suppliers]
        benchmarks[cid] = max(scores) if scores else 0

    # 3. per-criterion gap & relative %, 4. PPI
    for s in suppliers:
        rel_weighted = 0.0
        details = []
        for cr in s["validated"]["criteria"]:
            cid = cr["criterion_id"]
            bench = benchmarks[cid]
            gap = round(cr["score"] - bench, 2)
            if bench == 0:
                relative = 100.0
            else:
                relative = round((cr["score"] / bench) * 100, 2)
            rel_weighted += relative * weights.get(cid, 0.0)
            details.append({
                "criterion_id": cid,
                "name": cr["name"],
                "score": cr["score"],
                "max_score": cr["max_score"],
                "weight": weights.get(cid, 0.0),
                "benchmark": bench,
                "gap": gap,
                "relative_pct": relative,
                "evidence": cr["evidence"],
                "justification": cr["justification"],
            })
        s["ppi"] = round(rel_weighted / total_weight, 2) if total_weight else 0.0
        s["criterion_details"] = details

    # 5. deterministic tie-break sort
    def sort_key(s):
        return (
            -s["ppi"],
            _parse_date(s["submission_date"]),
            -float(s["experience_rating"]),
            s["supplier_name"].lower(),
        )

    ordered = sorted(suppliers, key=sort_key)
    for rank, s in enumerate(ordered, start=1):
        s["final_rank"] = rank

    return {
        "benchmarks": benchmarks,
        "suppliers": ordered,  # ranked order
        "tie_break_order": [
            "1) Higher Peer Performance Index (PPI)",
            "2) Earlier submission date",
            "3) Higher historical experience rating",
            "4) Supplier name (A-Z)",
        ],
    }
