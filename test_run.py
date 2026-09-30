"""End-to-end test: mock batch run + validation edge cases. Writes sample_output/sample_run.json"""
import json
import os
from pathlib import Path

# force mock backend
os.environ.pop("OPENAI_API_KEY", None)

from init_db import init_db
from tools.orchestrator import run_evaluation
from tools.validation_tool import validate_llm_result
from tools.orchestrator import load_active_criteria

BASE = Path(__file__).parent
DB = BASE / "rfp_evaluation.db"
PDF_DIR = BASE / "data" / "sample_pdfs"

init_db(DB)
criteria = load_active_criteria(DB)
print(f"Active criteria: {len(criteria)}, weights total={sum(c['weight'] for c in criteria)}")

profiles = [
    ("Apex Systems", "2026-09-10", 4.2, "Apex_Systems_RFP.pdf"),
    ("BrightPath Tech", "2026-09-08", 2.5, "BrightPath_Tech_RFP.pdf"),
    ("NexaWorks", "2026-09-12", 4.5, "NexaWorks_RFP.pdf"),
    ("Orbit Digital", "2026-09-09", 4.8, "Orbit_Digital_RFP.pdf"),
]
inputs = []
for name, sdate, exp, fn in profiles:
    p = PDF_DIR / fn
    assert p.exists(), f"missing {p}"
    inputs.append({"supplier_name": name, "submission_date": sdate,
                   "experience_rating": exp, "pdf_bytes": p.read_bytes(), "filename": fn})

result = run_evaluation(DB, inputs)
print(f"\nRFP_RUN_ID: {result['rfp_run_id']}  backend={result['llm_backend']}")
for s in result["ranking"]["suppliers"]:
    print(f"  Rank {s['final_rank']}: {s['supplier_name']:16s} abs={s['absolute_score']:5.2f} PPI={s['ppi']:6.2f}% date={s['submission_date']} exp={s['experience_rating']}")
print(f"Warnings: {len(result['warnings'])}")
for w in result["warnings"][:5]:
    print("   -", w)

# --- validation edge cases ---
print("\n--- Validation edge cases ---")
# 1. malformed: missing criteria, out-of-range score, bad types
bad_raw = {"supplier_name": "EdgeCo",
           "criteria": [{"criterion_id": 1, "score": 99, "max_score": 10, "evidence": "", "justification": "too high"},
                        {"criterion_id": 999, "score": 5},
                        {"criterion_id": "x", "score": "bad"}],
           "risks": "not-a-list", "overall_summary": "edge"}
norm, warns = validate_llm_result(bad_raw, criteria)
print(f"EdgeCo normalized scores: {[(c['criterion_id'], c['score']) for c in norm['criteria']]}")
print(f"EdgeCo warnings ({len(warns)}):")
for w in warns:
    print("   -", w)
assert all(0 <= c["score"] <= c["max_score"] for c in norm["criteria"]), "clipping failed"
assert len(norm["criteria"]) == len(criteria), "missing criteria not filled"

# 2. tie-break determinism: identical PPI -> earlier date wins
from tools.ranking_tool import compute_scores_and_ranking
s1 = {"supplier_name": "Beta", "submission_date": "2026-09-02", "experience_rating": 3.0,
      "validated": {"criteria": [{"criterion_id": c["criterion_id"], "name": c["name"], "score": 7.0,
                                  "max_score": 10, "evidence": "", "justification": ""} for c in criteria],
                    "risks": [], "overall_summary": ""}, "warnings": []}
s2 = {"supplier_name": "Alpha", "submission_date": "2026-09-01", "experience_rating": 3.0,
      "validated": {"criteria": [{"criterion_id": c["criterion_id"], "name": c["name"], "score": 7.0,
                                  "max_score": 10, "evidence": "", "justification": ""} for c in criteria],
                    "risks": [], "overall_summary": ""}, "warnings": []}
r = compute_scores_and_ranking([s1, s2], criteria)
order = [s["supplier_name"] for s in r["suppliers"]]
print(f"Tie-break order (expect Alpha first): {order}")
assert order == ["Alpha", "Beta"], "tie-break failed"

# write sample output
export = {
    "rfp_run_id": result["rfp_run_id"],
    "created_at": result["created_at"],
    "criteria": result["criteria"],
    "tie_break_order": result["ranking"]["tie_break_order"],
    "benchmarks": result["ranking"]["benchmarks"],
    "suppliers": [
        {"supplier_name": s["supplier_name"], "submission_date": s["submission_date"],
         "experience_rating": s["experience_rating"], "absolute_score": s["absolute_score"],
         "ppi": s["ppi"], "final_rank": s["final_rank"], "criterion_details": s["criterion_details"],
         "risks": s["validated"]["risks"], "overall_summary": s["validated"]["overall_summary"],
         "warnings": s["warnings"]} for s in result["ranking"]["suppliers"]
    ],
    "warnings": result["warnings"],
}
out = BASE / "sample_output" / "sample_run.json"
out.write_text(json.dumps(export, indent=2))
print(f"\nSample JSON written: {out} ({out.stat().st_size} bytes)")
print("ALL TESTS PASSED")
