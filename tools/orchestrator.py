"""Orchestrator Agent: controls the workflow and calls tools in order.

Steps: setup -> input -> batch -> evaluate -> validate -> score -> benchmark -> rank -> persist -> present
The LLM judges proposal content only; arithmetic/benchmarks/tie-breaks/ranks are deterministic Python.
"""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

from .document_tool import extract_text_from_pdf
from .llm_client import evaluate_supplier
from .validation_tool import validate_llm_result
from .ranking_tool import compute_scores_and_ranking

BASE_DIR = Path(__file__).parent.parent

def load_active_criteria(db_path: Path) -> List[Dict]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT criterion_id, name, description, weight, max_score FROM evaluation_criteria WHERE is_active=1 ORDER BY criterion_id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def run_evaluation(db_path: Path, supplier_inputs: List[Dict]) -> Dict:
    """
    supplier_inputs: [{"supplier_name": str, "submission_date": str, "experience_rating": float, "pdf_bytes": bytes, "filename": str}]
    Returns the complete run result dict (also persisted).
    """
    criteria = load_active_criteria(db_path)
    if not criteria:
        raise ValueError("No active evaluation criteria found. Run init_db.py first.")
    total_w = sum(c["weight"] for c in criteria)
    if abs(total_w - 100.0) > 0.01:
        raise ValueError(f"Active criteria weights total {total_w}%, must total 100%.")

    rfp_run_id = f"RFP-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    created_at = datetime.now(timezone.utc).isoformat()

    suppliers = []
    all_warnings = []
    for inp in supplier_inputs:
        name = inp["supplier_name"].strip()
        if not name:
            raise ValueError("Supplier name is required.")
        # 4a. extract
        try:
            text = extract_text_from_pdf(inp["pdf_bytes"])
        except Exception as e:
            raise ValueError(f"Could not extract text from {inp.get('filename', name)}: {e}")
        # 4b. evaluate via LLM agent
        raw = evaluate_supplier(name, criteria, text)
        raw["supplier_name"] = name  # enforce metadata name
        # 5. validate
        validated, warnings = validate_llm_result(raw, criteria)
        suppliers.append({
            "supplier_name": name,
            "submission_date": inp["submission_date"],
            "experience_rating": float(inp["experience_rating"]),
            "filename": inp.get("filename", ""),
            "validated": validated,
            "warnings": warnings,
            "text_chars": len(text),
        })
        for w in warnings:
            all_warnings.append(f"[{name}] {w}")

    # 6-8. score, benchmark, rank (deterministic)
    ranking = compute_scores_and_ranking(suppliers, criteria)

    # 9. persist
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("INSERT INTO rfp_runs (rfp_run_id, created_at, status) VALUES (?, ?, 'completed')",
                     (rfp_run_id, created_at))
        for s in ranking["suppliers"]:
            result_json = json.dumps({
                "supplier_name": s["supplier_name"],
                "submission_date": s["submission_date"],
                "experience_rating": s["experience_rating"],
                "absolute_score": s["absolute_score"],
                "ppi": s["ppi"],
                "final_rank": s["final_rank"],
                "criterion_details": s["criterion_details"],
                "risks": s["validated"]["risks"],
                "overall_summary": s["validated"]["overall_summary"],
                "warnings": s["warnings"],
            }, indent=2)
            conn.execute(
                """INSERT INTO supplier_results
                   (rfp_run_id, supplier_name, submission_date, experience_rating, absolute_score, ppi, final_rank, result_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (rfp_run_id, s["supplier_name"], s["submission_date"], s["experience_rating"],
                 s["absolute_score"], s["ppi"], s["final_rank"], result_json),
            )
        conn.commit()
    finally:
        conn.close()

    return {
        "rfp_run_id": rfp_run_id,
        "created_at": created_at,
        "criteria": criteria,
        "ranking": ranking,
        "warnings": all_warnings,
        "llm_backend": "openai" if __import__("os").environ.get("OPENAI_API_KEY") else "mock",
    }
