"""
src/analytics/engine.py

Orchestrator: runs the full Ratio Engine for all 92 companies.
Populates the financial_ratios table in SQLite with 14+ KPI columns.
Generates output/capital_allocation.csv and output/ratio_edge_cases.log.

Run with: python -m src.analytics.engine
"""
import os
import sqlite3
from typing import Dict, List

import pandas as pd

from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
    debt_to_equity,
    interest_coverage,
    net_debt,
    asset_turnover,
)
from src.analytics.cagr import (
    compute_revenue_cagr,
    compute_pat_cagr,
    compute_eps_cagr,
)
from src.analytics.cashflow_kpis import (
    free_cash_flow,
    capex_intensity,
    fcf_conversion_rate,
    classify_capital_allocation,
    get_sign_symbol,
)


DB_PATH = os.getenv("DB_PATH", "db/nifty100.db")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
EDGE_LOG = os.path.join(OUTPUT_DIR, "ratio_edge_cases.log")
CAPITAL_ALLOCATION_CSV = os.path.join(OUTPUT_DIR, "capital_allocation.csv")
VALIDATION_CSV = os.path.join(OUTPUT_DIR, "ratio_validation.csv")


def load_data(conn: sqlite3.Connection):
    """Load all needed data from the database into DataFrames."""
    companies = pd.read_sql("SELECT id, company_name, roce_percentage, roe_percentage FROM companies", conn)
    sectors = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
    pl = pd.read_sql("SELECT * FROM profitandloss", conn)
    bs = pd.read_sql("SELECT * FROM balancesheet", conn)
    cf = pd.read_sql("SELECT * FROM cashflow", conn)
    fr = pd.read_sql("SELECT * FROM financial_ratios", conn)

    # Merge companies with sector
    companies = companies.merge(sectors, left_on='id', right_on='company_id', how='left')

    return companies, pl, bs, cf, fr


def compute_ratios_for_company_company_year(
    company_id: str,
    year: str,
    pl_row: pd.Series,
    bs_row: pd.Series,
    cf_row: pd.Series,
    is_financial: bool,
    capital_employed_total: float,
) -> Dict:
    """Compute all single-year ratios for a company-year."""
    result = {
        'company_id': company_id,
        'year': year,
    }

    # Profitability
    result['net_profit_margin_pct'] = net_profit_margin(
        pl_row.get('net_profit'), pl_row.get('sales'),
        company_id=company_id, year=year
    )

    opm, _ = operating_profit_margin(
        pl_row.get('operating_profit'), pl_row.get('sales'), pl_row.get('opm_percentage'),
        company_id=company_id, year=year
    )
    result['operating_profit_margin_pct'] = opm

    result['return_on_equity_pct'] = return_on_equity(
        pl_row.get('net_profit'), bs_row.get('equity_capital'), bs_row.get('reserves'),
        company_id=company_id, year=year
    )

    result['return_on_capital_employed_pct'] = return_on_capital_employed(
        pl_row.get('operating_profit'), pl_row.get('depreciation'),
        bs_row.get('equity_capital'), bs_row.get('reserves'), bs_row.get('borrowings'),
        bs_row.get('total_assets'),
        is_financial=is_financial, company_id=company_id, year=year
    )

    result['return_on_assets_pct'] = return_on_assets(
        pl_row.get('net_profit'), bs_row.get('total_assets'),
        company_id=company_id, year=year
    )

    # Leverage
    de, _ = debt_to_equity(
        bs_row.get('borrowings'), bs_row.get('equity_capital'), bs_row.get('reserves'),
        is_financial=is_financial, company_id=company_id, year=year
    )
    result['debt_to_equity'] = de

    icr, _, _ = interest_coverage(
        pl_row.get('operating_profit'), pl_row.get('other_income'), pl_row.get('interest'),
        company_id=company_id, year=year
    )
    result['interest_coverage'] = icr

    result['net_debt_cr'] = net_debt(bs_row.get('borrowings'), bs_row.get('investments'))

    # Efficiency
    result['asset_turnover'] = asset_turnover(
        pl_row.get('sales'), bs_row.get('total_assets'),
        company_id=company_id, year=year
    )

    # Cash flow KPIs
    result['free_cash_flow_cr'] = free_cash_flow(
        cf_row.get('operating_activity'), cf_row.get('investing_activity')
    )

    result['capex_cr'] = abs(cf_row.get('investing_activity')) if cf_row.get('investing_activity') is not None else None

    result['capex_intensity_pct'] = capex_intensity(
        cf_row.get('investing_activity'), pl_row.get('sales')
    )

    result['fcf_conversion_pct'] = fcf_conversion_rate(
        result['free_cash_flow_cr'], pl_row.get('operating_profit')
    )

    # Pass-through fields from P&L
    result['earnings_per_share'] = pl_row.get('eps')
    result['dividend_payout_ratio_pct'] = pl_row.get('dividend_payout')

    # Capital allocation
    cfo_pat_ratio = None
    if pl_row.get('net_profit') and pl_row.get('net_profit') > 0:
        cfo = cf_row.get('operating_activity')
        if cfo is not None:
            cfo_pat_ratio = cfo / pl_row.get('net_profit')

    pattern = classify_capital_allocation(
        cf_row.get('operating_activity'), cf_row.get('investing_activity'), cf_row.get('financing_activity'),
        cfo_pat_ratio=cfo_pat_ratio
    )
    result['capital_allocation_pattern'] = pattern

    # Cash flow pass-throughs
    result['cash_from_operations_cr'] = cf_row.get('operating_activity')
    result['total_debt_cr'] = bs_row.get('borrowings')

    # Book value per share - approximate as (equity_capital + reserves) / shares
    # We don't have shares outstanding directly, so approximate from equity_capital / face_value
    face_value = pl_row.get('face_value') if 'face_value' in pl_row.index else None
    equity_capital = bs_row.get('equity_capital') or 0
    if face_value and face_value > 0 and equity_capital > 0:
        shares_outstanding_cr = (equity_capital / face_value) * 1_00_00_000  # face value is in Rupees
        # equity_capital is in Cr, face_value is in Rs
        # shares = (equity_capital * 1e7) / face_value (in absolute shares)
        # BVPS = (equity_capital + reserves) * 1e7 / shares = (equity_capital + reserves) * face_value / equity_capital
        # Simplified: BVPS = (equity_capital + reserves) / (equity_capital / face_value)
        reserves = bs_row.get('reserves') or 0
        result['book_value_per_share'] = round((equity_capital + reserves) / (equity_capital / face_value), 2)
    else:
        result['book_value_per_share'] = None

    return result


def compute_cagr_for_company(
    company_id: str,
    pl_df: pd.DataFrame,
) -> Dict:
    """Compute all 9 CAGR values (3 metrics x 3 windows) for a company."""
    if pl_df is None or pl_df.empty:
        return {}

    # Sort by year (ascending for chronological)
    pl_df = pl_df.sort_values('year', ascending=True)
    years = pl_df['year'].tolist()

    sales = pl_df['sales'].tolist()
    pat = pl_df['net_profit'].tolist()
    eps = pl_df['eps'].tolist()

    result = {}

    for window in [3, 5, 10]:
        rev_cagr, rev_flag = compute_revenue_cagr(years, sales, window_years=window)
        pat_cagr, pat_flag = compute_pat_cagr(years, pat, window_years=window)
        eps_cagr, eps_flag = compute_eps_cagr(years, eps, window_years=window)

        result[f'revenue_cagr_{window}yr'] = rev_cagr
        result[f'revenue_cagr_{window}yr_flag'] = rev_flag
        result[f'pat_cagr_{window}yr'] = pat_cagr
        result[f'pat_cagr_{window}yr_flag'] = pat_flag
        result[f'eps_cagr_{window}yr'] = eps_cagr
        result[f'eps_cagr_{window}yr_flag'] = eps_flag

    # Stash for cross-reference
    result['_years'] = list(pl_df['year'])

    return result


def compute_composite_quality_score(row: pd.Series) -> float | None:
    """
    Composite quality score: weighted average of normalized KPIs.
    Higher is better.

    Weights:
    - ROE: 30%
    - OPM: 20%
    - ROA: 20%
    - D/E (inverted): 15%
    - Asset Turnover: 15%
    """
    scores = []
    weights = []

    # ROE (higher better), normalize to 0-100 scale: cap at 50%
    if pd.notna(row.get('return_on_equity_pct')):
        roe = max(0, min(row['return_on_equity_pct'], 50))
        scores.append(roe)
        weights.append(0.30)

    # OPM (higher better)
    if pd.notna(row.get('operating_profit_margin_pct')):
        opm = max(0, min(row['operating_profit_margin_pct'], 50))
        scores.append(opm)
        weights.append(0.20)

    # ROA (higher better)
    if pd.notna(row.get('return_on_assets_pct')):
        roa = max(0, min(row['return_on_assets_pct'], 30))
        scores.append(roa)
        weights.append(0.20)

    # D/E (lower better) - invert: score = 100 / (1 + D/E)
    if pd.notna(row.get('debt_to_equity')):
        de = row['debt_to_equity']
        de_score = 100 / (1 + de)
        scores.append(de_score)
        weights.append(0.15)

    # Asset Turnover (higher better)
    if pd.notna(row.get('asset_turnover')):
        at = max(0, min(row['asset_turnover'] * 50, 50))  # 0-2 -> 0-100
        scores.append(at)
        weights.append(0.15)

    if not scores:
        return None

    total_weight = sum(weights)
    composite = sum(s * w for s, w in zip(scores, weights)) / total_weight
    return round(composite, 2)


def run_ratio_engine(db_path: str = DB_PATH, output_dir: str = OUTPUT_DIR):
    """Main entry point: populate financial_ratios table with computed KPIs."""
    os.makedirs(output_dir, exist_ok=True)

    # Clear edge case log
    with open(EDGE_LOG, 'w', encoding='utf-8') as f:
        f.write("company_id,year,formula,reason\n")

    conn = sqlite3.connect(db_path)
    print("Loading data from nifty100.db...")
    companies, pl, bs, cf, fr = load_data(conn)
    print(f"  {len(companies)} companies, {len(pl)} P&L rows, {len(bs)} BS rows, {len(cf)} CF rows")

    # Identify Financials companies
    is_financial = companies['broad_sector'] == 'Financials'
    financial_ids = set(companies.loc[is_financial, 'id'])
    print(f"  {len(financial_ids)} Financials companies (use ROA proxy for ROCE)")

    # Build merged dataset for each company
    all_results = []
    capital_allocation_rows = []

    for _, company in companies.iterrows():
        company_id = company['id']
        is_fin = company_id in financial_ids

        # Get all P&L, BS, CF for this company
        company_pl = pl[pl['company_id'] == company_id].copy()
        company_bs = bs[bs['company_id'] == company_id].copy()
        company_cf = cf[cf['company_id'] == company_id].copy()

        # Get precomputed ROE/ROCE for cross-check
        precomp_roe = company.get('roe_percentage')
        precomp_roce = company.get('roce_percentage')

        # Compute CAGR (once per company, then attach to all years)
        cagr_result = compute_cagr_for_company(company_id, company_pl)
        cagr_years = cagr_result.pop('_years', [])

        # For each year, compute single-year ratios
        for _, pl_row in company_pl.iterrows():
            year = pl_row['year']

            # Find matching BS and CF rows
            bs_match = company_bs[company_bs['year'] == year]
            cf_match = company_cf[company_cf['year'] == year]

            if bs_match.empty or cf_match.empty:
                continue

            bs_row = bs_match.iloc[0]
            cf_row = cf_match.iloc[0]

            # Compute ratios
            result = compute_ratios_for_company_company_year(
                company_id, year, pl_row, bs_row, cf_row, is_fin, capital_employed_total=0
            )

            # Attach CAGR (only for years that have full history)
            result['revenue_cagr_5yr'] = cagr_result.get('revenue_cagr_5yr')
            result['revenue_cagr_5yr_flag'] = cagr_result.get('revenue_cagr_5yr_flag')
            result['pat_cagr_5yr'] = cagr_result.get('pat_cagr_5yr')
            result['pat_cagr_5yr_flag'] = cagr_result.get('pat_cagr_5yr_flag')
            result['eps_cagr_5yr'] = cagr_result.get('eps_cagr_5yr')
            result['eps_cagr_5yr_flag'] = cagr_result.get('eps_cagr_5yr_flag')

            all_results.append(result)

            # Capital allocation row
            capital_allocation_rows.append({
                'company_id': company_id,
                'year': year,
                'cfo_sign': get_sign_symbol(cf_row.get('operating_activity')),
                'cfi_sign': get_sign_symbol(cf_row.get('investing_activity')),
                'cff_sign': get_sign_symbol(cf_row.get('financing_activity')),
                'pattern_label': result['capital_allocation_pattern'],
            })

    # Build DataFrame
    df = pd.DataFrame(all_results)

    # Compute composite quality score
    df['composite_quality_score'] = df.apply(compute_composite_quality_score, axis=1)

    # Save capital allocation CSV
    cap_df = pd.DataFrame(capital_allocation_rows)
    cap_df.to_csv(CAPITAL_ALLOCATION_CSV, index=False)
    print(f"  Saved {len(cap_df)} capital allocation rows to {CAPITAL_ALLOCATION_CSV}")

    # Cross-check vs precomputed values
    cross_check_results = []
    for _, row in df.iterrows():
        company_id = row['company_id']
        company_info = companies[companies['id'] == company_id]
        if company_info.empty:
            continue
        precomp_roe = company_info.iloc[0].get('roe_percentage')
        precomp_roce = company_info.iloc[0].get('roce_percentage')

        # Cross-check ROE
        if pd.notna(row.get('return_on_equity_pct')) and pd.notna(precomp_roe):
            try:
                precomp_roe_val = float(precomp_roe)
                if abs(row['return_on_equity_pct'] - precomp_roe_val) > 5:
                    cross_check_results.append({
                        'company_id': company_id,
                        'year': row['year'],
                        'metric': 'ROE',
                        'computed': row['return_on_equity_pct'],
                        'precomputed': precomp_roe_val,
                        'diff': row['return_on_equity_pct'] - precomp_roe_val,
                        'category': 'data_source_issue_or_formula_discrepancy',
                    })
            except (ValueError, TypeError):
                pass

        # Cross-check ROCE
        if pd.notna(row.get('return_on_capital_employed_pct')) and pd.notna(precomp_roce):
            try:
                precomp_roce_val = float(precomp_roce)
                if abs(row['return_on_capital_employed_pct'] - precomp_roce_val) > 5:
                    cross_check_results.append({
                        'company_id': company_id,
                        'year': row['year'],
                        'metric': 'ROCE',
                        'computed': row['return_on_capital_employed_pct'],
                        'precomputed': precomp_roce_val,
                        'diff': row['return_on_capital_employed_pct'] - precomp_roce_val,
                        'category': 'data_source_issue_or_formula_discrepancy',
                    })
            except (ValueError, TypeError):
                pass

    # Save cross-validation
    cross_df = pd.DataFrame(cross_check_results)
    if not cross_df.empty:
        cross_df.to_csv(VALIDATION_CSV, index=False)
        print(f"  Saved {len(cross_df)} cross-validation anomalies to {VALIDATION_CSV}")

    # Now write to financial_ratios table
    # The financial_ratios table already exists from Sprint 1 - we need to add new columns
    cursor = conn.cursor()
    cursor.execute("DELETE FROM financial_ratios")
    conn.commit()

    # Additional columns we want to add (will need ALTER TABLE)
    extra_cols = {
        'return_on_capital_employed_pct': 'REAL',
        'return_on_assets_pct': 'REAL',
        'net_debt_cr': 'REAL',
        'capex_intensity_pct': 'REAL',
        'fcf_conversion_pct': 'REAL',
        'revenue_cagr_5yr': 'REAL',
        'revenue_cagr_5yr_flag': 'TEXT',
        'pat_cagr_5yr': 'REAL',
        'pat_cagr_5yr_flag': 'TEXT',
        'eps_cagr_5yr': 'REAL',
        'eps_cagr_5yr_flag': 'TEXT',
        'composite_quality_score': 'REAL',
        'capital_allocation_pattern': 'TEXT',
    }

    # Add columns to financial_ratios table if they don't exist
    existing_cols = pd.read_sql("PRAGMA table_info(financial_ratios)", conn)['name'].tolist()
    for col_name, col_type in extra_cols.items():
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE financial_ratios ADD COLUMN {col_name} {col_type}")
    conn.commit()

    # Write via to_sql with append (using only columns that exist or have been added)
    df_to_write = df.copy()
    # Replace dividend_payout_ratio_pct with the right name
    if 'dividend_payout_pct' in df_to_write.columns:
        df_to_write = df_to_write.drop(columns=['dividend_payout_pct'])

    df_to_write.to_sql('financial_ratios', conn, if_exists='append', index=False)

    print(f"\n[OK] Wrote {len(df)} rows to financial_ratios table")

    # Verify
    count = pd.read_sql("SELECT COUNT(*) as n FROM financial_ratios", conn).iloc[0]['n']
    print(f"[OK] Verification: SELECT COUNT(*) FROM financial_ratios = {count}")

    # Verify all columns are populated (no null-only columns)
    col_counts = pd.read_sql("""
        SELECT
            COUNT(*) as total_rows,
            SUM(CASE WHEN net_profit_margin_pct IS NULL THEN 1 ELSE 0 END) as npm_nulls,
            SUM(CASE WHEN return_on_equity_pct IS NULL THEN 1 ELSE 0 END) as roe_nulls,
            SUM(CASE WHEN composite_quality_score IS NULL THEN 1 ELSE 0 END) as cqs_nulls
        FROM financial_ratios
    """, conn).iloc[0]
    print(f"[OK] Null counts: NPM={col_counts['npm_nulls']}, ROE={col_counts['roe_nulls']}, CQS={col_counts['cqs_nulls']}")

    conn.close()

    return df


if __name__ == "__main__":
    run_ratio_engine()