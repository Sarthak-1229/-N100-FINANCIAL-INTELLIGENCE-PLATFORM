"""
src/etl/loader.py

The ETL pipeline: Extract (read Excel) -> Transform (normalise + validate)
-> Load (write to SQLite). Run with:  python -m src.etl.loader

Design:
  * Parent table (companies) loads FIRST, so we have the valid-ticker set
    needed for every child table's FK check (DQ-03).
  * Every load_xxx() function returns an AuditRow so main() can build
    output/load_audit.csv without each function knowing about the others.
  * Every rejected/flagged row appends a Violation to a shared list,
    written once at the end to output/validation_failures.csv.
"""
import csv
import os
import sqlite3
from dataclasses import dataclass, asdict

import pandas as pd
from dotenv import load_dotenv

from src.etl.normaliser import (
    normalize_year, normalize_ticker, normalize_numeric, parse_analysis_metric,
)
from src.etl import validator as dq

load_dotenv()

RAW_DIR = os.getenv("RAW_DATA_DIR", "data/raw")
DB_PATH = os.getenv("DB_PATH", "db/nifty100.db")
SCHEMA_PATH = os.getenv("SCHEMA_PATH", "db/schema.sql")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
MIN_YEARS = int(os.getenv("DQ_MIN_YEARS_COVERAGE", 5))

VIOLATIONS: list[dq.Violation] = []


@dataclass
class AuditRow:
    table: str
    rows_read: int
    rows_loaded: int
    rows_rejected: int
    critical_failures: int
    warning_flags: int


AUDIT: list[AuditRow] = []


def _read_core(name: str) -> pd.DataFrame:
    """Core files: row 0 = title, row 1 = real header."""
    return pd.read_excel(f"{RAW_DIR}/{name}.xlsx", header=1)


def _read_supp(name: str) -> pd.DataFrame:
    """Supplementary files: clean header on row 0."""
    return pd.read_excel(f"{RAW_DIR}/{name}.xlsx")


def _log(rule_id, severity, table, identifier, message):
    VIOLATIONS.append(dq.Violation(rule_id, severity, table, str(identifier), message))


def build_schema(conn: sqlite3.Connection):
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())


# ── 1. companies ─────────────────────────────────────────────────────
def load_companies(conn) -> set:
    df = _read_core("companies")
    rows_read = len(df)
    df["id"] = df["id"].apply(normalize_ticker)

    bad_ticker = df[df["id"].isna()]
    for _, r in bad_ticker.iterrows():
        _log("DQ-08", "CRITICAL", "companies", r.get("id"), "Ticker failed format check")
    df = df.dropna(subset=["id"])

    dupes = dq.check_company_pk_uniqueness(df["id"].tolist())
    if dupes:
        for d in set(dupes):
            _log("DQ-01", "CRITICAL", "companies", d, "Duplicate company id — HALTS load per spec")
        raise SystemExit(f"DQ-01 CRITICAL: duplicate company ids found: {set(dupes)}. Load halted.")

    cols = ["id", "company_name", "company_logo", "chart_link", "about_company",
            "website", "nse_profile", "bse_profile", "face_value", "book_value",
            "roce_percentage", "roe_percentage"]
    df = df[cols]

    df.to_sql("companies", conn, if_exists="append", index=False)
    AUDIT.append(AuditRow("companies", rows_read, len(df), rows_read - len(df),
                           len(bad_ticker), 0))
    return set(df["id"])


# ── shared logic for profitandloss / balancesheet / cashflow ────────
def _load_period_table(conn, name: str, valid_tickers: set, rename: dict,
                        year_col: str, numeric_cols: list, extra_checks=None,
                        reader=_read_core):
    """
    Generic loader for tables shaped like company_id + year + numeric cols.
    `reader` picks _read_core (title row on line 0) vs _read_supp (clean
    header on line 0) -- financial_ratios is a *supplementary* file but
    still has messy year strings like the 3 core statement tables.
    """
    df = reader(name)
    rows_read = len(df)

    df["company_id"] = df["company_id"].apply(normalize_ticker)
    df["year_norm"] = df[year_col].apply(normalize_year)
    for c in numeric_cols:
        df[c] = df[c].apply(normalize_numeric)

    critical = 0
    # DQ-07: unparseable year -> reject
    bad_year = df["year_norm"].isna()
    for _, r in df[bad_year].iterrows():
        _log("DQ-07", "CRITICAL", name, r["company_id"], f"Unparseable year: {r[year_col]!r}")
    critical += bad_year.sum()
    df = df[~bad_year]

    # DQ-03: FK integrity -> reject orphans
    orphan_mask = ~df["company_id"].isin(valid_tickers)
    for _, r in df[orphan_mask].iterrows():
        _log("DQ-03", "CRITICAL", name, r["company_id"], "company_id not found in companies table")
    critical += orphan_mask.sum()
    df = df[~orphan_mask]

    # DQ-02: duplicate (company_id, year) -> keep last occurrence, log the rest
    dup_mask = df.duplicated(subset=["company_id", "year_norm"], keep="last")
    for _, r in df[dup_mask].iterrows():
        _log("DQ-02", "CRITICAL", name, f"{r['company_id']}/{r['year_norm']}",
             "Duplicate (company_id, year) — kept last occurrence")
    critical += dup_mask.sum()
    df = df[~dup_mask]

    warnings = 0
    if extra_checks:
        warnings = extra_checks(df, name)

    df = df.rename(columns=rename)
    # Overwrite the raw year column with the normalised one explicitly
    # (can't just rename year_norm->year: if year_col is already 'year',
    # that produces two same-named columns and pandas silently keeps
    # the wrong one -- this bug shipped once already, caught in Day 6
    # manual review).
    df["year"] = df["year_norm"]
    out_cols = ["company_id", "year"] + list(rename.values())
    df_out = df[out_cols]

    df_out.to_sql(name, conn, if_exists="append", index=False)
    AUDIT.append(AuditRow(name, rows_read, len(df_out), rows_read - len(df_out),
                           int(critical), int(warnings)))


def _pl_extra_checks(df, name):
    warnings = 0
    for _, r in df.iterrows():
        if not dq.check_positive_sales(r["sales"]):
            _log("DQ-06", "WARNING", name, r["company_id"], f"Non-positive sales: {r['sales']}")
            warnings += 1
        if r["opm_percentage"] is not None and r["operating_profit"] is not None and r["sales"]:
            if not dq.check_opm_crosscheck(r["opm_percentage"], r["operating_profit"], r["sales"]):
                _log("DQ-05", "WARNING", name, r["company_id"], "OPM cross-check mismatch")
                warnings += 1
        if r["tax_percentage"] is not None and not dq.check_tax_rate_range(r["tax_percentage"]):
            _log("DQ-11", "WARNING", name, r["company_id"], f"Tax rate out of [0,60]: {r['tax_percentage']}")
            warnings += 1
        if r["dividend_payout"] is not None and not dq.check_dividend_payout(r["dividend_payout"]):
            _log("DQ-12", "WARNING", name, r["company_id"], f"Dividend payout > 200%: {r['dividend_payout']}")
            warnings += 1
        if not dq.check_eps_sign(r["eps"], r["net_profit"]):
            _log("DQ-14", "WARNING", name, r["company_id"], "EPS sign inconsistent with net_profit")
            warnings += 1
    return warnings


def _bs_extra_checks(df, name):
    warnings = 0
    for _, r in df.iterrows():
        if not dq.check_bs_balance(r["total_assets"], r["total_liabilities"]):
            _log("DQ-04", "WARNING", name, r["company_id"],
                 f"Balance mismatch: assets={r['total_assets']} liab={r['total_liabilities']}")
            warnings += 1
        if not dq.check_bs_strict_balance(r["total_assets"], r["total_liabilities"]):
            _log("DQ-15", "INFO", name, r["company_id"], "Not exactly balanced (informational)")
        fa, flagged = dq.coerce_nonneg_fixed_assets(r["fixed_assets"])
        if flagged:
            _log("DQ-10", "WARNING", name, r["company_id"], f"Negative fixed_assets coerced to 0")
            warnings += 1
            df.at[r.name, "fixed_assets"] = fa
    return warnings


def _cf_extra_checks(df, name):
    warnings = 0
    for _, r in df.iterrows():
        if not dq.check_net_cash(r["net_cash_flow"], r["operating_activity"],
                                  r["investing_activity"], r["financing_activity"]):
            _log("DQ-09", "WARNING", name, r["company_id"], "net_cash_flow doesn't reconcile with CFO+CFI+CFF")
            warnings += 1
    return warnings


def load_profitandloss(conn, valid_tickers):
    rename = {
        "sales": "sales", "expenses": "expenses", "operating_profit": "operating_profit",
        "opm_percentage": "opm_percentage", "other_income": "other_income",
        "interest": "interest", "depreciation": "depreciation",
        "profit_before_tax": "profit_before_tax", "tax_percentage": "tax_percentage",
        "net_profit": "net_profit", "eps": "eps", "dividend_payout": "dividend_payout",
    }
    numeric = list(rename.keys())
    _load_period_table(conn, "profitandloss", valid_tickers, rename, "year", numeric, _pl_extra_checks)


def load_balancesheet(conn, valid_tickers):
    rename = {c: c for c in ["equity_capital", "reserves", "borrowings", "other_liabilities",
                              "total_liabilities", "fixed_assets", "cwip", "investments",
                              "other_asset", "total_assets"]}
    _load_period_table(conn, "balancesheet", valid_tickers, rename, "year", list(rename.keys()), _bs_extra_checks)


def load_cashflow(conn, valid_tickers):
    rename = {c: c for c in ["operating_activity", "investing_activity",
                              "financing_activity", "net_cash_flow"]}
    _load_period_table(conn, "cashflow", valid_tickers, rename, "year", list(rename.keys()), _cf_extra_checks)


def load_financial_ratios(conn, valid_tickers):
    rename = {c: c for c in [
        "net_profit_margin_pct", "operating_profit_margin_pct", "return_on_equity_pct",
        "debt_to_equity", "interest_coverage", "asset_turnover", "free_cash_flow_cr",
        "capex_cr", "earnings_per_share", "book_value_per_share",
        "dividend_payout_ratio_pct", "total_debt_cr", "cash_from_operations_cr"]}
    _load_period_table(conn, "financial_ratios", valid_tickers, rename, "year", list(rename.keys()),
                        reader=_read_supp)


# ── analysis : sparse, text-encoded metrics ─────────────────────────
def load_analysis(conn, valid_tickers):
    df = _read_core("analysis")
    rows_read = len(df)
    df["company_id"] = df["company_id"].apply(normalize_ticker)

    orphan_mask = ~df["company_id"].isin(valid_tickers)
    critical = int(orphan_mask.sum())
    for _, r in df[orphan_mask].iterrows():
        _log("DQ-03", "CRITICAL", "analysis", r["company_id"], "orphan FK")
    df = df[~orphan_mask]

    recs = []
    for _, r in df.iterrows():
        sales_p, sales_v = parse_analysis_metric(r["compounded_sales_growth"])
        _, profit_v = parse_analysis_metric(r["compounded_profit_growth"])
        _, cagr_v = parse_analysis_metric(r["stock_price_cagr"])
        _, roe_v = parse_analysis_metric(r["roe"])
        recs.append({"company_id": r["company_id"], "period_years": sales_p,
                      "sales_growth_pct": sales_v, "profit_growth_pct": profit_v,
                      "stock_price_cagr_pct": cagr_v, "roe_pct": roe_v})
    out = pd.DataFrame(recs)
    out.to_sql("analysis", conn, if_exists="append", index=False)
    AUDIT.append(AuditRow("analysis", rows_read, len(out), rows_read - len(out), critical, 0))


# ── documents ─────────────────────────────────────────────────────
def load_documents(conn, valid_tickers):
    df = _read_core("documents")
    rows_read = len(df)
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    df = df.rename(columns={"Year": "year", "Annual_Report": "annual_report_url"})

    orphan_mask = ~df["company_id"].isin(valid_tickers)
    critical = int(orphan_mask.sum())
    for _, r in df[orphan_mask].iterrows():
        _log("DQ-03", "CRITICAL", "documents", r["company_id"], "orphan FK")
    df = df[~orphan_mask]

    dup_mask = df.duplicated(subset=["company_id", "year"], keep="last")
    critical += int(dup_mask.sum())
    for _, r in df[dup_mask].iterrows():
        _log("DQ-02", "CRITICAL", "documents", f"{r['company_id']}/{r['year']}", "duplicate (company_id, year)")
    df = df[~dup_mask]

    df_out = df[["company_id", "year", "annual_report_url"]]
    df_out.to_sql("documents", conn, if_exists="append", index=False)
    AUDIT.append(AuditRow("documents", rows_read, len(df_out), rows_read - len(df_out), critical, 0))
    # DQ-13 (URL reachability) is deliberately NOT run here -- see validator.py docstring.


# ── prosandcons ──────────────────────────────────────────────────
def load_prosandcons(conn, valid_tickers):
    df = _read_core("prosandcons")
    rows_read = len(df)
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    orphan_mask = ~df["company_id"].isin(valid_tickers)
    critical = int(orphan_mask.sum())
    for _, r in df[orphan_mask].iterrows():
        _log("DQ-03", "CRITICAL", "prosandcons", r["company_id"], "orphan FK")
    df = df[~orphan_mask]
    df_out = df[["company_id", "pros", "cons"]]
    df_out.to_sql("prosandcons", conn, if_exists="append", index=False)
    AUDIT.append(AuditRow("prosandcons", rows_read, len(df_out), rows_read - len(df_out), critical, 0))


# ── sectors ─────────────────────────────────────────────────────
def load_sectors(conn, valid_tickers):
    df = _read_supp("sectors")
    rows_read = len(df)
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    orphan_mask = ~df["company_id"].isin(valid_tickers)
    critical = int(orphan_mask.sum())
    for _, r in df[orphan_mask].iterrows():
        _log("DQ-03", "CRITICAL", "sectors", r["company_id"], "orphan FK")
    df = df[~orphan_mask]
    df_out = df[["company_id", "broad_sector", "sub_sector", "index_weight_pct", "market_cap_category"]]
    df_out.to_sql("sectors", conn, if_exists="append", index=False)
    AUDIT.append(AuditRow("sectors", rows_read, len(df_out), rows_read - len(df_out), critical, 0))


# ── stock_prices ─────────────────────────────────────────────────
def load_stock_prices(conn, valid_tickers):
    df = _read_supp("stock_prices")
    rows_read = len(df)
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    orphan_mask = ~df["company_id"].isin(valid_tickers)
    critical = int(orphan_mask.sum())
    for _, r in df[orphan_mask].iterrows():
        _log("DQ-03", "CRITICAL", "stock_prices", r["company_id"], "orphan FK")
    df = df[~orphan_mask]

    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    dup_mask = df.duplicated(subset=["company_id", "date"], keep="last")
    critical += int(dup_mask.sum())
    df = df[~dup_mask]

    df_out = df[["company_id", "date", "open_price", "high_price", "low_price",
                 "close_price", "volume", "adjusted_close"]]
    df_out.to_sql("stock_prices", conn, if_exists="append", index=False)
    AUDIT.append(AuditRow("stock_prices", rows_read, len(df_out), rows_read - len(df_out), critical, 0))


# ── market_cap ─────────────────────────────────────────────────
def load_market_cap(conn, valid_tickers):
    df = _read_supp("market_cap")
    rows_read = len(df)
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    orphan_mask = ~df["company_id"].isin(valid_tickers)
    critical = int(orphan_mask.sum())
    for _, r in df[orphan_mask].iterrows():
        _log("DQ-03", "CRITICAL", "market_cap", r["company_id"], "orphan FK")
    df = df[~orphan_mask]

    dup_mask = df.duplicated(subset=["company_id", "year"], keep="last")
    critical += int(dup_mask.sum())
    df = df[~dup_mask]

    df_out = df[["company_id", "year", "market_cap_crore", "enterprise_value_crore",
                 "pe_ratio", "pb_ratio", "ev_ebitda", "dividend_yield_pct"]]
    df_out.to_sql("market_cap", conn, if_exists="append", index=False)
    AUDIT.append(AuditRow("market_cap", rows_read, len(df_out), rows_read - len(df_out), critical, 0))


# ── peer_groups ─────────────────────────────────────────────────
def load_peer_groups(conn, valid_tickers):
    df = _read_supp("peer_groups")
    rows_read = len(df)
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    orphan_mask = ~df["company_id"].isin(valid_tickers)
    critical = int(orphan_mask.sum())
    for _, r in df[orphan_mask].iterrows():
        _log("DQ-03", "CRITICAL", "peer_groups", r["company_id"], "orphan FK")
    df = df[~orphan_mask]
    df["is_benchmark"] = df["is_benchmark"].astype(bool).astype(int)
    df_out = df[["peer_group_name", "company_id", "is_benchmark"]]
    df_out.to_sql("peer_groups", conn, if_exists="append", index=False)
    AUDIT.append(AuditRow("peer_groups", rows_read, len(df_out), rows_read - len(df_out), critical, 0))


# ── DQ-16 : coverage check (run after all period tables are loaded) ─
def check_coverage_all(conn):
    cur = conn.execute("""
        SELECT company_id, COUNT(DISTINCT year) as n
        FROM profitandloss GROUP BY company_id
    """)
    low_coverage = [(cid, n) for cid, n in cur.fetchall() if not dq.check_coverage(n, MIN_YEARS)]
    for cid, n in low_coverage:
        _log("DQ-16", "WARNING", "profitandloss", cid, f"Only {n} years of history (< {MIN_YEARS})")
    return low_coverage


def write_outputs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(f"{OUTPUT_DIR}/load_audit.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(AUDIT[0]).keys()))
        writer.writeheader()
        for row in AUDIT:
            writer.writerow(asdict(row))

    with open(f"{OUTPUT_DIR}/validation_failures.csv", "w", newline="") as f:
        fieldnames = ["rule_id", "severity", "table", "identifier", "message"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for v in VIOLATIONS:
            writer.writerow(asdict(v))


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)  # fresh load every time `make load` runs

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    build_schema(conn)

    valid_tickers = load_companies(conn)
    load_profitandloss(conn, valid_tickers)
    load_balancesheet(conn, valid_tickers)
    load_cashflow(conn, valid_tickers)
    load_analysis(conn, valid_tickers)
    load_documents(conn, valid_tickers)
    load_prosandcons(conn, valid_tickers)
    load_sectors(conn, valid_tickers)
    load_stock_prices(conn, valid_tickers)
    load_market_cap(conn, valid_tickers)
    load_financial_ratios(conn, valid_tickers)
    load_peer_groups(conn, valid_tickers)
    check_coverage_all(conn)

    conn.commit()

    fk_problems = conn.execute("PRAGMA foreign_key_check;").fetchall()

    write_outputs()

    n_critical = sum(1 for v in VIOLATIONS if v.severity == "CRITICAL")
    n_warning = sum(1 for v in VIOLATIONS if v.severity == "WARNING")
    print(f"Load complete. {len(AUDIT)} tables loaded.")
    print(f"Violations logged: {n_critical} CRITICAL, {n_warning} WARNING")
    print(f"PRAGMA foreign_key_check rows: {len(fk_problems)} (must be 0)")
    for row in AUDIT:
        print(f"  {row.table:18s} read={row.rows_read:5d}  loaded={row.rows_loaded:5d}  rejected={row.rows_rejected:4d}")

    conn.close()


if __name__ == "__main__":
    main()
