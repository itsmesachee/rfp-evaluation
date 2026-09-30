-- SQLite schema for Agentic RFP Evaluation
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS evaluation_criteria (
    criterion_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    weight REAL NOT NULL,        -- percentage, active weights should total 100
    max_score INTEGER NOT NULL DEFAULT 10,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS rfp_runs (
    rfp_run_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed'
);

CREATE TABLE IF NOT EXISTS supplier_results (
    rfp_run_id TEXT NOT NULL,
    supplier_name TEXT NOT NULL,
    submission_date TEXT NOT NULL,       -- ISO date YYYY-MM-DD
    experience_rating REAL NOT NULL,     -- e.g. 1.0 - 5.0
    absolute_score REAL NOT NULL,
    ppi REAL NOT NULL,
    final_rank INTEGER NOT NULL,
    result_json TEXT NOT NULL,            -- full per-supplier result JSON
    PRIMARY KEY (rfp_run_id, supplier_name),
    FOREIGN KEY (rfp_run_id) REFERENCES rfp_runs(rfp_run_id) ON DELETE CASCADE
);
