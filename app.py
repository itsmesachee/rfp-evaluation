"""Streamlit app: RFP Ranker — agentic supplier evaluation and ranking."""
import json
import sqlite3
from datetime import date
from pathlib import Path

import streamlit as st

from tools.orchestrator import load_active_criteria, run_evaluation
from tools import llm_client

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "rfp_evaluation.db"

st.set_page_config(page_title="RFP Ranker — Agentic Supplier Evaluation", layout="wide")

# ---------- Light theme accents (white background + color coding) ----------
st.markdown("""
<style>
/* Primary buttons: solid accent */
.stButton > button[kind="primary"] {
    background-color: #4A90D9;
    border-color: #4A90D9;
    color: #FFFFFF;
    border-radius: 10px;
    font-weight: 600;
}
/* Expander cards: soft blue tint */
[data-testid="stExpander"] {
    background-color: #F2F7FD;
    border: 1px solid #D6E4F0;
    border-radius: 10px;
}
/* Metric cards (top suppliers): soft blue tint */
[data-testid="stMetric"] {
    background-color: #F2F7FD;
    border: 1px solid #D6E4F0;
    border-radius: 10px;
    padding: 12px;
}
/* Accent bar on section headers */
h2 {
    border-left: 6px solid #4A90D9;
    padding-left: 12px;
}
</style>
""", unsafe_allow_html=True)


# ---------- Sidebar: optional user-supplied LLM key (e.g. OpenRouter) ----------
with st.sidebar:
    st.header("Configuration")
    user_key = st.text_input(
        "LLM API key (OpenRouter)", type="password",
        help="Optional. Paste your own key to score with a real LLM. "
             "Leave empty to use the built-in mock evaluator.")
    user_model = st.text_input(
        "Model", value="openai/gpt-4o-mini",
        help="OpenRouter model id, e.g. openai/gpt-4o-mini")
    if user_key.strip():
        llm_client.configure(api_key=user_key, model=user_model,
                             base_url=llm_client.OPENROUTER_BASE_URL)
    st.caption(f"Active backend: **{llm_client.backend_name()}**")

# Ensure DB exists
if not DB_PATH.exists():
    st.warning("Database not found — initializing with seed criteria...")
    from init_db import init_db
    init_db(DB_PATH)

st.title("🏆📋 Agentic RFP Evaluation & Supplier Ranking")
st.caption("Agentic supplier evaluation: an LLM reads each proposal and scores it against "
           "your criteria, then deterministic Python computes benchmarks, PPI, tie-breaks "
           "and the final ranking.")

with st.expander("How it works"):
    st.write("Upload RFP PDFs → the orchestrator extracts text → the LLM scores every active "
             "criterion as evidence-grounded JSON → validation normalizes the results → Python "
             "computes absolute scores, peer benchmarks and PPI → suppliers are ranked with a "
             "fixed tie-break order → everything is persisted in SQLite under one run ID.")

# ---------- Criteria ----------
st.header("Evaluation criteria")
st.caption("Loaded live from the SQLite criteria table. Active weights must total 100%.")
criteria = load_active_criteria(DB_PATH)
total_w = sum(c["weight"] for c in criteria)
if criteria:
    st.dataframe(
        [{"Criterion": c["name"], "Weight (%)": c["weight"],
          "Max score": c["max_score"], "What the LLM assesses": c["description"]}
         for c in criteria],
        use_container_width=True, hide_index=True)
st.write(f"**Total active weight:** {total_w}%")
if abs(total_w - 100.0) > 0.01:
    st.error("Active criteria weights must total 100%. Update evaluation_criteria in SQLite.")
st.caption(f"Scoring backend: **{llm_client.backend_name()}** — add a key in the sidebar "
           "or set OPENAI_API_KEY to use a real JSON-capable LLM.")

st.divider()

# ---------- Supplier input ----------
st.header("Proposals")
st.write("Upload supplier RFP PDFs, then add details for each proposal.")

uploaded = st.file_uploader("Supplier RFP documents (PDF)", type=["pdf"], accept_multiple_files=True)

supplier_inputs = []
if uploaded:
    st.subheader("Proposal details")
    for i, f in enumerate(uploaded):
        with st.expander(f"📄 {f.name}", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                default_name = Path(f.name).stem.replace("_", " ").replace(" RFP", "")
                name = st.text_input("Supplier", value=default_name, key=f"name_{i}")
            with c2:
                sub_date = st.date_input("Submitted on", value=date.today(), key=f"date_{i}")
            with c3:
                exp = st.number_input("Track record (1–5)", min_value=1.0, max_value=5.0,
                                      value=3.5, step=0.5, key=f"exp_{i}")
            supplier_inputs.append({
                "supplier_name": name,
                "submission_date": sub_date.isoformat(),
                "experience_rating": float(exp),
                "pdf_bytes": f.getvalue(),
                "filename": f.name,
            })

score = st.button("⚖️ Score proposals", type="primary", disabled=not supplier_inputs)
if score:
    names = [s["supplier_name"].strip() for s in supplier_inputs]
    if any(not n for n in names):
        st.error("Validation: each proposal needs a supplier name.")
    elif len(set(n.lower() for n in names)) != len(names):
        st.error("Validation: supplier names must be unique within a batch.")
    else:
        with st.spinner("Evaluating: extracting text → LLM scoring → validation → ranking..."):
            try:
                result = run_evaluation(DB_PATH, supplier_inputs)
                st.session_state["last_run"] = result
                st.success(f"Done — run ID: {result['rfp_run_id']}")
            except Exception as e:
                st.error(f"Evaluation failed: {e}")

# ---------- Results ----------
result = st.session_state.get("last_run")
if result:
    ranking = result["ranking"]
    suppliers = ranking["suppliers"]
    top = suppliers[0]

    st.header("Results")
    st.success(f"🏆 Winner: **{top['supplier_name']}** — {top['absolute_score']}/100 · PPI {top['ppi']}%")

    st.subheader("Top suppliers")
    cols = st.columns(min(3, len(suppliers)))
    for col, s in zip(cols, suppliers[:3]):
        with col:
            st.metric(f"#{s['final_rank']} {s['supplier_name']}",
                      f"{s['absolute_score']} pts", f"PPI {s['ppi']}%")

    st.subheader("Ranking")
    st.dataframe(
        [{"Rank": s["final_rank"], "Supplier": s["supplier_name"],
          "Absolute score (/100)": s["absolute_score"], "PPI (%)": s["ppi"],
          "Submission date": s["submission_date"], "Experience": s["experience_rating"]}
         for s in suppliers],
        use_container_width=True, hide_index=True)

    st.subheader("Scorecards")
    for s in suppliers:
        with st.expander(f"#{s['final_rank']} · {s['supplier_name']} — "
                         f"{s['absolute_score']}/100 · PPI {s['ppi']}%"):
            st.write(f"**Summary:** {s['validated']['overall_summary']}")
            st.dataframe(
                [{"Criterion": d["name"], "Score": f"{d['score']}/{d['max_score']}",
                  "Weight": f"{d['weight']}%", "Benchmark": d["benchmark"],
                  "Gap": d["gap"], "Relative %": d["relative_pct"]}
                 for d in s["criterion_details"]],
                use_container_width=True, hide_index=True)
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

    st.subheader("Run summary")
    st.code(f"Run ID: {result['rfp_run_id']}\n"
            f"Created: {result['created_at']}\n"
            f"LLM backend: {result['llm_backend']}")
    st.write("**Tie-breaks applied (in order):**")
    for i, t in enumerate(ranking["tie_break_order"], start=1):
        st.write(f"{i}. {t}")
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
            } for s in suppliers
        ],
    }
    st.download_button("Download result (JSON)", data=json.dumps(export, indent=2),
                       file_name=f"{result['rfp_run_id']}.json", mime="application/json")

st.divider()
st.header("Previous runs")
st.caption("Stored in SQLite (rfp_runs table).")
conn = sqlite3.connect(str(DB_PATH))
try:
    runs = conn.execute("SELECT rfp_run_id, created_at, status FROM rfp_runs ORDER BY created_at DESC LIMIT 10").fetchall()
    if runs:
        st.dataframe([{"Run ID": r[0], "Created": r[1], "Status": r[2]} for r in runs],
                     use_container_width=True, hide_index=True)
    else:
        st.caption("No runs yet.")
finally:
    conn.close()
