# Sprint 1 Retrospective — Data Foundation

## What we built
A full ETL pipeline (`loader.py`, `normaliser.py`, `validator.py`) that reads
all 12 source Excel files, normalises messy years/tickers, runs all 16 DQ
rules, and loads a validated `nifty100.db` with 12 tables.

## Key decisions (documented, not silent)
- **12 tables instead of the spec's ambiguous "10 tables" list.** The task
  brief and the master PDF spec disagreed slightly on the exact table
  count/names. Since we have all 12 source files, we loaded all 12 —
  simplest and most complete. `financial_ratios.xlsx` is loaded as-is here;
  Sprint 2's Ratio Engine will recompute it independently as a cross-check.
- **`normalize_year()` defaults bare years (e.g. "2013") to March (`-03`)**
  since that's the modal fiscal year-end in this dataset (~95%+ of rows).
  This is a documented assumption, not a silent guess — flagged in the
  function's docstring.
- **`"TTM"` (trailing twelve months) is rejected**, not mapped to a year —
  it isn't a fiscal year-end and would corrupt year-over-year comparisons.

## Bug found during Day 6 manual review
`_load_period_table()` renamed the normalised year column (`year_norm`) to
`year` — but the *raw* messy year column was already called `year` for
P&L/BS/CF. This created two same-named columns; pandas silently kept the
wrong (raw, unnormalised) one. Caught by eyeballing real output ("Mar 2024"
instead of "2024-03"), not by any automated test. Fixed, and a regression
test (`test_loader_regressions.py`) now guards against it recurring.
**Lesson: automated tests catch what you thought to test for. Manual
review catches what you didn't.**

## Data quality findings (real issues in the source data, not our bugs)
- **8 tickers appear in child tables but not in `companies.xlsx`**:
  ULTRACEMCO, UNIONBANK, UNITDSPR, VBL, VEDL, WIPRO, ZOMATO, ZYDUSLIFE.
  These are genuinely missing from the companies master file (92 of 100
  Nifty100 constituents are present). Every row referencing them was
  rejected per DQ-03 and logged.
- **JIOFIN has only 2 years of history** — correctly flagged by DQ-16
  (Jio Financial Services was only listed in 2023, so this is real, not
  a bug).
- **DQ-05 (OPM cross-check) is the largest WARNING category (228 rows)** —
  worth a follow-up in Sprint 2: the source's `opm_percentage` may use a
  formula that differs slightly from `operating_profit / sales`.

## Exit criteria — final status

| Criterion | Result |
|---|---|
| `SELECT COUNT(*) FROM companies` = 92 | ✅ 92 |
| `PRAGMA foreign_key_check` → 0 rows | ✅ 0 rows |
| `load_audit.csv` → zero CRITICAL issues in the *loaded* data | ✅ all 784 CRITICAL rows were rejected before insert, not silently loaded |
| 35+ ETL unit tests pass | ✅ 101 passed |
| Manual review: 5 companies correct | ✅ SUNPHARMA, BAJFINANCE, ADANIGREEN, HAL, EICHERMOT reviewed; 1 bug found + fixed |
| Sprint review signed off | ⏳ pending your review of this document |

## Carried into Sprint 2
- Recompute `financial_ratios` independently via the Ratio Engine and
  diff against the loaded reference values.
- Investigate the DQ-05 OPM formula discrepancy.
- Optional: run `check_url_reachable()` (DQ-13) as a separate, slower
  batch job against the 1,456 loaded `documents` URLs — not run during
  every `make load` since it's network-dependent and would make the
  pipeline flaky.
