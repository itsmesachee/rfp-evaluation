"""Streamlit app: Agentic RFP Evaluation and Supplier Ranking."""
import json
import sqlite3
from datetime import date
from pathlib import Path

import streamlit as st

from tools.orchestrator import load_active_criteria, run_evaluation
from tools import llm_client

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "rfp_evaluation.db"

st.set_page_config(page_title="Agentic RFP Evaluation", layout="wide")

# ---------- Sidebar: optional user-supplied LLM key (e.g. OpenRouter) ----------
with st.sidebar:
    st.header("⚙️ Settings")
    user_key = st.text_input(
        "OpenRouter API Key", type="password",
        help="Optional. Paste your own key to score with a real LLM. "
             "Leave empty to use the built-in mock evaluator.")
    user_model = st.text_input(
        "Model", value="openai/gpt-4o-mini",
        help="OpenRouter model id, e.g. openai/gpt-4o-mini")
    if user_key.strip():
        llm_client.configure(api_key=user_key, model=user_model,
                             base_url=llm_client.OPENROUTER_BASE_URL)
    st.caption(f"LLM backend: **{llm_client.backend_name()}**")

# Ensure DB exists
if not DB_PATH.exists():
    st.warning("Database not found — initializing with seed criteria...")
    from init_db import init_db
    init_db(DB_PATH)

st.title("📋 Agentic RFP Evaluation & Supplier Ranking")
st.caption("AI-assisted proposal scoring with deterministic ranking. LLM judges content; Python decides the math.")

# ---------- Screen: Criteria ----------
st.header("1. Evaluation Criteria (from SQLite)")
criteria = load_active_criteria(DB_PATH)
total_w = sum(c["weight"] for c in criteria)
cols = st.columns(len(criteria)) if criteria else []
for col, c in zip(cols, criteria):
    with col:
        st.metric(c["name"], f'{c["weight"]}%', f'max {c["max_score"]}')
        st.caption(c["description"])
st.write(f"**Total active weight:** {total_w}%")
if abs(total_w - 100.0) > 0.01:
    st.error("Active criteria weights must total 100%. Update evaluation_criteria in SQLite.")
st.info(f"LLM backend: **{llm_client.backend_name()}** — paste a key in the sidebar, or set OPENAI_API_KEY, to use a real JSON-capable LLM.")

# ---------- Screen: Supplier input ----------
st.header("2. Supplier Input")
st.write("Upload multiple supplier RFP PDFs, then enter metadata per file.")

uploaded = st.file_uploader("Upload supplier RFP PDFs", type=["pdf"], accept_multiple_files=True)

supplier_inputs = []
if uploaded:
    st.subheader("Supplier metadata")
    for i, f in enumerate(uploaded):
        with st.expander(f"📄 {f.name}", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                default_name = Path(f.name).stem.replace("_", " ").replace(" RFP", "")
                name = st.text_input("Supplier name", value=default_name, key=f"name_{i}")
            with c2:
                sub_date = st.date_input("Submission date", value=date.today(), key=f"date_{i}")
            with c3:
                exp = st.number_input("Historical experience rating (1-5)", min_value=1.0, max_value=5.0,
                                      value=3.5, step=0.5, key=f"exp_{i}")
            supplier_inputs.append({
                "supplier_name": name,
                "submission_date": sub_date.isoformat(),
                "experience_rating": float(exp),
                "pdf_bytes": f.getvalue(),
                "filename": f.name,
            })

evaluate = st.button("🚀 Evaluate Batch", type="primary", disabled=not supplier_inputs)
if evaluate:
    names = [s["supplier_name"].strip() for s in supplier_inputs]
    if any(not n for n in names):
        st.error("Validation: every supplier needs a name.")
    elif len(set(n.lower() for n in names)) != len(names):
        st.error("Validation: supplier names must be unique within a batch.")
    else:
        with st.spinner("Orchestrator running: extract → LLM evaluate → validate → score → benchmark → rank → persist..."):
            try:
                result = run_evaluation(DB_PATH, supplier_inputs)
                st.session_state["last_run"] = result
                st.success(f"Batch evaluated. RFP_RUN_ID = {result['rfp_run_id']}")
            except Exception as e:
                st.error(f"Evaluation failed: {e}")

# ---------- Screens: Leaderboard / Scorecards / Run details ----------
result = st.session_state.get("last_run")
if result:
    ranking = result["ranking"]
    st.header("3. Leaderboard")
    lb_rows = [{
        "Rank": s["final_rank"],
        "Supplier": s["supplier_name"],
        "Absolute score (/100)": s["absolute_score"],
        "PPI (%)": s["ppi"],
        "Submission date": s["submission_date"],
        "Experience": s["experience_rating"],
    } for s in ranking["suppliers"]]
    st.dataframe(lb_rows, use_container_width=True, hide_index=True)

    st.header("4. Detailed Scorecards")
    for s in ranking["suppliers"]:
        with st.expander(f"#{s['final_rank']} {s['supplier_name']} — abs {s['absolute_score']}, PPI {s['ppi']}%"):
            st.write(f"**Summary:** {s['validated']['overall_summary']}")
            det_rows = [{
                "Criterion": d["name"],
                "Score": f"{d['score']}/{d['max_score']}",
                "Weight": f"{d['weight']}%",
                "Benchmark": d["benchmark"],
                "Gap": d["gap"],
                "Relative %": d["relative_pct"],
            } for d in s["criterion_details"]]
            st.dataframe(det_rows, use_container_width=True, hide_index=True)
            for d in s["criterion_details"]:
                st.markdown(f"**{d['name']}** ({d['score']}/{d['max_score']})")
                st.caption(f"Justification: {d['justification']}")
                if d["evidence"]:
                    st.caption(f"Evidence: “{d['evidence']}”")
            if s["validated"]["risks"]:
                st.write("**Risks:**")
                for r in s["validated"]["risks"]:
                    st.write(f"- {r}")
            if s["warnings"]:
                st.warning("Validation warnings: " + "; ".join(s["warnings"]))

    st.header("5. Run Details")
    st.code(f"RFP_RUN_ID: {result['rfp_run_id']}\nCreated: {result['created_at']}\nLLM backend: {result['llm_backend']}")
    st.write("**Tie-break order applied:**")
    for t in ranking["tie_break_order"]:
        st.write(f"- {t}")
    if result["warnings"]:
        st.subheader("Warnings")
        for w in result["warnings"]:
            st.write(f"- {w}")
    else:
        st.write("No validation warnings.")

    export = {
        "rfp_run_id": result["rfp_run_id"],
        "created_at": result["created_at"],
        "llm_backend": result["llm_backend"],
        "criteria": result["criteria"],
        "tie_break_order": ranking["tie_break_order"],
        "benchmarks": ranking["benchmarks"],
        "suppliers": [
            {
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
            } for s in ranking["suppliers"]
        ],
    }
    st.download_button("⬇️ Download complete result as JSON", data=json.dumps(export, indent=2),
                       file_name=f"{result['rfp_run_id']}.json", mime="application/json")

st.divider()
st.header("Past runs (SQLite)")
conn = sqlite3.connect(str(DB_PATH))
try:
    runs = conn.execute("SELECT rfp_run_id, created_at, status FROM rfp_runs ORDER BY created_at DESC LIMIT 10").fetchall()
    if runs:
        st.dataframe([{"RFP_RUN_ID": r[0], "Created": r[1], "Status": r[2]} for r in runs],
                     use_container_width=True, hide_index=True)
    else:
        st.caption("No runs yet.")
finally:
    conn.close()
