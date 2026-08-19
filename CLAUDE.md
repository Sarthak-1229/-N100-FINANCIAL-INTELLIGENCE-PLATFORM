# CLAUDE.md — Nifty 100 Financial Intelligence Platform
# Claude Code reads this file first, every session. Follow it exactly.

## What this project is
A full-stack financial analytics platform over 92 Nifty 100 companies.
Raw Excel files → SQLite database → KPI engine → screener → dashboard → REST API.
Built over 45 days in 6 sprints. Each sprint's tasks are given to you as text.
All monetary values are in Indian Rupees — Crore (Cr) unless stated otherwise.

## Your job each session
You receive a sprint's task description as text (pasted in).
You implement it fully: write code, run it, fix errors, run tests, fix failures.
Do not stop and ask "shall I continue?" — keep going until all tests pass and
all deliverables exist. Only stop if you hit a genuine ambiguity that requires
a business decision (e.g. "which formula should win when source disagrees?").

## Project structure
```
data/raw/               12 source Excel files — READ ONLY, never modify
db/
  schema.sql            SQLite schema (12 tables)
  nifty100.db           generated database (gitignored)
src/
  etl/
    loader.py           ETL pipeline entry point: python -m src.etl.loader
    normaliser.py       normalize_year(), normalize_ticker(), normalize_numeric()
    validator.py        DQ-01..DQ-16 rule functions
  analytics/
    ratios.py           Sprint 2: ratio engine entry point
    cagr.py             Sprint 2: CAGR calculations
    cashflow_kpis.py    Sprint 2: FCF, capital allocation
  screener/             Sprint 3
  dashboard/            Sprint 4
  reports/              Sprint 5
  api/                  Sprint 6
tests/
  etl/                  Sprint 1 tests (101 passing — do not break these)
  kpi/                  Sprint 2 tests
  screener/             Sprint 3 tests
output/                 generated CSVs (gitignored)
logs/                   runtime logs (gitignored)
notebooks/              SQL queries, exploration
CLAUDE.md               this file
SPRINT1_RETROSPECTIVE.md
```

## Commands to run (Windows PowerShell, venv active)
```powershell
python -m src.etl.loader          # load / reload the database
python -m src.analytics.ratios    # Sprint 2: compute all KPIs
pytest tests/ -v                  # run ALL tests — must stay 0 failures
pytest tests/kpi/ -v              # run only KPI tests
```

## Non-negotiable coding rules
1. **Never modify data/raw/*.xlsx** — they are read-only source files.
2. **Always run pytest tests/ after any change** — Sprint 1's 101 tests must
   keep passing. New code must add tests, never remove them.
3. **All monetary values in Crore (Cr)** unless a column name says otherwise.
4. **Edge cases are not optional.** Every ratio function must handle:
   - Division by zero → return None (not crash, not 0, not inf)
   - Negative denominator (e.g. negative equity) → return None
   - Missing/null inputs → return None
   - Debt-free companies (borrowings=0) → Interest Coverage = None, display as "Debt Free"
5. **Log, don't silently drop.** Every edge case hit must be written to
   output/ratio_edge_cases.log with company_id, year, formula, reason.
6. **One function = one formula.** Keep ratios.py, cagr.py, cashflow_kpis.py
   as separate files. Each function should be 5-15 lines. Tiny = testable.
7. **Cross-validate against the source.** After computing ratios, compare
   a 5-company sample against financial_ratios.xlsx (already loaded in DB).
   Log discrepancies > 2% to output/ratio_validation.csv.
8. **Banks/NBFCs get special treatment for D/E.** Use sectors.broad_sector
   to detect financials. Do not flag D/E > 5 as abnormal for banks.
   Use ROA instead of ROE for bank ROCE calculation.

## Sprint completion criteria — how to know when you're done
- Sprint 1: `SELECT COUNT(*) FROM companies` = 92; PRAGMA foreign_key_check = 0; 101 tests pass
- Sprint 2: financial_ratios table has 1000+ rows; all KPI tests pass; ratio_edge_cases.log exists; cross-validation sample within ±2%
- Sprint 3: 6 preset screeners produce output; peer_percentiles table built; all screener tests pass
- Sprint 4: streamlit run src/dashboard/app.py launches without error; all 8 screens render
- Sprint 5: 92 tearsheet PDFs generated in reports/tearsheets/; pros_cons_generated.csv exists
- Sprint 6: All API endpoints return correct data; 60+ total tests pass

## Data quality decisions (already made — do not re-litigate)
- normalize_year("TTM") → None (reject, not a fiscal year)
- normalize_year("2013") → "2013-03" (assume March fiscal year-end)
- Companies missing from companies.xlsx (WIPRO, VEDL, etc.) → rejected with DQ-03 log
- JIOFIN has 2 years only → correct, not a bug (listed 2023)
- DQ-05 OPM mismatch (228 rows) → WARNING only, investigate in Sprint 2

## Key formulas for Sprint 2
All inputs come from the SQLite tables, not raw Excel.
```
NPM   = net_profit / sales * 100
OPM   = operating_profit / sales * 100  [cross-check vs opm_percentage ±1%]
ROE   = net_profit / (equity_capital + reserves) * 100
ROCE  = (operating_profit - depreciation) / (equity_capital + reserves + borrowings) * 100
        [banks: use net_profit / total_assets * 100 instead]
D/E   = borrowings / (equity_capital + reserves)
        [0 for debt-free; flag > 5 for non-financials only]
ICR   = (operating_profit + other_income) / interest
        [None if interest = 0, display "Debt Free"]
FCF   = operating_activity + investing_activity
AT    = sales / total_assets
CAGR  = ((end / start) ^ (1/n) - 1) * 100
        [None if base <= 0; add "turnaround" flag if base < 0 and end > 0]
Capital allocation: sign(CFO), sign(CFI), sign(CFF) → 8-pattern label
```

## Sector benchmark ranges (for anomaly detection, Sprint 3+)
| Sector            | ROE     | D/E     | OPM     |
|---|---|---|---|
| Banks             | 12-22%  | >5x OK  | NIM proxy |
| NBFC              | 12-20%  | 3-8x OK | NIM proxy |
| IT                | 25-50%  | 0-0.3x  | 20-35%  |
| FMCG              | 20-45%  | 0-0.5x  | 15-28%  |
| Pharma            | 15-30%  | 0-0.8x  | 15-25%  |
| Energy (Oil/Gas)  | 10-18%  | 0.5-2x  | 8-18%   |
| Energy (Power)    | 8-15%   | 1-4x OK | 25-40%  |
| Consumer Disc.    | 10-25%  | 0.3-1.5x| 10-20%  |
| Materials         | 10-25%  | 0.3-1x  | 12-22%  |
| Industrials       | 12-22%  | 0.3-1.5x| 10-20%  |

## What NOT to do
- Do not use `make` — it is not installed on Windows. Use python/pytest directly.
- Do not hardcode file paths with backslashes. Use os.path.join() or pathlib.
- Do not load from data/raw/*.xlsx in Sprint 2+ — always query nifty100.db.
- Do not delete or modify existing tests in tests/etl/.
- Do not commit nifty100.db, .env, venv/, output/*.csv, logs/*.log (gitignored).
- Do not use pd.read_excel in analytics/ — that's ETL's job. Use sqlite3 or pandas.read_sql.
- Do not silently swallow exceptions. Log them and re-raise or return None with a log entry.