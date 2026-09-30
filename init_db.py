"""
Initialize SQLite DB and seed evaluation criteria.
Run: python init_db.py [--db path]
"""
import argparse
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DEFAULT_DB = BASE_DIR / "rfp_evaluation.db"
SCHEMA_FILE = BASE_DIR / "db_schema.sql"

SEED_CRITERIA = [
    (1, "Technical Capability", "Architecture, integrations, scalability, technical fit", 30.0, 10, 1),
    (2, "Implementation Plan", "Timeline, milestones, staffing, risk plan", 20.0, 10, 1),
    (3, "Commercial Value", "Pricing clarity, total cost, assumptions", 20.0, 10, 1),
    (4, "Security & Compliance", "Controls, certifications, privacy, auditability", 20.0, 10, 1),
    (5, "Support & Experience", "Support model, similar projects, references", 10.0, 10, 1),
]

def init_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_FILE.read_text()
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(schema)
        # Clear and reseed criteria for reproducibility
        conn.execute("DELETE FROM evaluation_criteria")
        conn.executemany(
            "INSERT INTO evaluation_criteria (criterion_id, name, description, weight, max_score, is_active) VALUES (?, ?, ?, ?, ?, ?)",
            SEED_CRITERIA,
        )
        conn.commit()
        # Validate weights total 100
        cur = conn.execute("SELECT SUM(weight) FROM evaluation_criteria WHERE is_active=1")
        total = cur.fetchone()[0] or 0
        print(f"DB initialized at {db_path}")
        print(f"Seeded {len(SEED_CRITERIA)} criteria, active weight total = {total}%")
        if abs(total - 100.0) > 0.001:
            print("WARNING: active weights do not total 100%")
    finally:
        conn.close()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=str(DEFAULT_DB))
    args = p.parse_args()
    init_db(Path(args.db))
