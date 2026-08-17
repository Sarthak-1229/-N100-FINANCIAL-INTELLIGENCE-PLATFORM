# Nifty 100 Financial Intelligence Platform

Sprint 1 — Data Foundation (Days 1-7) — COMPLETE

## Setup
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
make load     # builds db/nifty100.db from data/raw/*.xlsx
make test     # runs 101 unit tests
```

## Structure
```
data/raw/       12 source Excel files
db/             schema.sql + generated nifty100.db (12 tables)
src/etl/        loader.py, normaliser.py, validator.py
tests/etl/      101 unit tests
notebooks/      exploratory_queries.sql (10 queries)
output/         load_audit.csv, validation_failures.csv (generated)
SPRINT1_RETROSPECTIVE.md   full writeup: decisions, bugs found, exit criteria
```

## Sprint 1 results
- companies loaded: 92
- FK integrity: PRAGMA foreign_key_check = 0 rows
- 784 CRITICAL + 340 WARNING DQ issues found and logged (all CRITICAL rows rejected, not loaded)
- 101/101 unit tests passing
- See SPRINT1_RETROSPECTIVE.md for full detail and Sprint 2 handoff notes
