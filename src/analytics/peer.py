"""
src/analytics/peer.py

Peer Percentile Engine - computes percentile rankings within peer groups.
Metrics: ROE, ROCE, NPM, D/E (inverted), FCF, PAT CAGR 5yr, Revenue CAGR 5yr,
EPS CAGR 5yr, ICR, Asset Turnover
"""
import os
import sqlite3
import pandas as pd


DB_PATH = os.getenv("DB_PATH", "db/nifty100.db")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")


# Metrics to rank with direction (higher_is_better=True means higher percentile = better)
METRICS_CONFIG = [
    {'name': 'ROE', 'column': 'return_on_equity_pct', 'higher_is_better': True},
    {'name': 'ROCE', 'column': 'return_on_capital_employed_pct', 'higher_is_better': True},
    {'name': 'NPM', 'column': 'net_profit_margin_pct', 'higher_is_better': True},
    {'name': 'DE', 'column': 'debt_to_equity', 'higher_is_better': False},  # Lower is better
    {'name': 'FCF', 'column': 'free_cash_flow_cr', 'higher_is_better': True},
    {'name': 'PAT_CAGR_5YR', 'column': 'pat_cagr_5yr', 'higher_is_better': True},
    {'name': 'REVENUE_CAGR_5YR', 'column': 'revenue_cagr_5yr', 'higher_is_better': True},
    {'name': 'EPS_CAGR_5YR', 'column': 'eps_cagr_5yr', 'higher_is_better': True},
    {'name': 'ICR', 'column': 'interest_coverage', 'higher_is_better': True},
    {'name': 'ASSET_TURNOVER', 'column': 'asset_turnover', 'higher_is_better': True},
]


def get_peer_groups(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load peer groups from database."""
    query = """
        SELECT pg.peer_group_name, pg.company_id, pg.is_benchmark,
               c.company_name, s.broad_sector, s.sub_sector
        FROM peer_groups pg
        JOIN companies c ON pg.company_id = c.id
        LEFT JOIN sectors s ON pg.company_id = s.company_id
    """
    return pd.read_sql(query, conn)


def get_latest_financial_data(conn: sqlite3.Connection, year: str = "2024-03") -> pd.DataFrame:
    """Load latest financial_ratios + market_cap for the given year."""
    query = """
        SELECT
            fr.*,
            mc.pe_ratio,
            mc.pb_ratio,
            mc.dividend_yield_pct,
            mc.market_cap_crore
        FROM financial_ratios fr
        LEFT JOIN market_cap mc ON fr.company_id = mc.company_id
            AND CAST(mc.year AS TEXT) = ?
        WHERE fr.year = ?
    """
    return pd.read_sql(query, conn, params=[year[:4], year])


def compute_percentile_rank(series: pd.Series, invert: bool = False) -> pd.Series:
    """
    Compute percentile rank (0 to 1) for a series.

    Args:
        series: Values to rank
        invert: If True, higher values get lower percentiles (for D/E)

    Returns:
        Series with percentile ranks (0-1)
    """
    if series.isna().all():
        return pd.Series(0.5, index=series.index)  # Neutral rank for all-NaN

    # Use rank with pct=True for percentile rank
    # method='average' handles ties by averaging their ranks
    ranks = series.rank(pct=True, method='average')

    if invert:
        ranks = 1 - ranks

    return ranks


def compute_peer_percentiles(year: str = "2024-03", db_path: str = DB_PATH):
    """
    Main function to compute peer percentiles and populate peer_percentiles table.

    For each peer group, computes percentile rank for each of the 10 metrics.
    D/E is inverted so lower D/E = higher percentile.

    Args:
        year: Fiscal year to use for latest data
        db_path: Path to SQLite database
    """
    conn = sqlite3.connect(db_path)

    # Get peer groups
    peer_groups = get_peer_groups(conn)
    if peer_groups.empty:
        print("No peer groups found in database")
        conn.close()
        return

    print(f"Found {len(peer_groups)} peer group assignments across {peer_groups['peer_group_name'].nunique()} groups")

    # Get financial data
    financial_data = get_latest_financial_data(conn, year)
    print(f"Loaded financial data for {len(financial_data)} companies for year {year}")

    # Merge financial data with peer groups
    merged = peer_groups.merge(
        financial_data,
        left_on='company_id',
        right_on='company_id',
        how='left'
    )

    # Create peer_percentiles table if not exists
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS peer_percentiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL REFERENCES companies(id),
            peer_group_name TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL,
            percentile_rank REAL,  -- 0.0 to 1.0
            year TEXT NOT NULL,
            UNIQUE(company_id, peer_group_name, metric, year)
        )
    """)
    conn.commit()

    # Clear existing data for this year
    cursor.execute("DELETE FROM peer_percentiles WHERE year = ?", [year])
    conn.commit()

    # For each peer group, compute percentiles
    all_results = []

    for group_name in merged['peer_group_name'].unique():
        group_data = merged[merged['peer_group_name'] == group_name].copy()

        print(f"\nProcessing peer group: {group_name} ({len(group_data)} companies)")

        # For each metric, compute percentile rank within this group
        for metric_config in METRICS_CONFIG:
            metric_name = metric_config['name']
            column = metric_config['column']
            higher_is_better = metric_config['higher_is_better']

            if column not in group_data.columns:
                print(f"  Warning: Column {column} not found for {metric_name}")
                continue

            # Get valid values for this metric
            valid_data = group_data.dropna(subset=[column])
            if valid_data.empty:
                print(f"  Warning: No valid data for {metric_name}")
                continue

            # Compute percentile rank
            invert = not higher_is_better
            pct_ranks = compute_percentile_rank(valid_data[column], invert=invert)

            # Create result rows
            for idx, row in valid_data.iterrows():
                all_results.append({
                    'company_id': row['company_id'],
                    'peer_group_name': group_name,
                    'metric': metric_name,
                    'value': row[column],
                    'percentile_rank': pct_ranks[idx],
                    'year': year
                })

            print(f"  {metric_name}: {len(valid_data)} companies ranked")

    # Insert into database
    if all_results:
        results_df = pd.DataFrame(all_results)
        results_df.to_sql('peer_percentiles', conn, if_exists='append', index=False)
        print(f"\nInserted {len(results_df)} percentile records into peer_percentiles table")

    # Generate output CSV summary
    output_path = os.path.join(OUTPUT_DIR, "peer_groups_summary.csv")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if all_results:
        summary_df = pd.DataFrame(all_results)
        # Pivot for easier reading: rows = company, columns = metrics
        pivot = summary_df.pivot_table(
            index=['company_id', 'peer_group_name'],
            columns='metric',
            values=['value', 'percentile_rank'],
            aggfunc='first'
        )
        pivot.to_csv(output_path)
        print(f"Saved peer groups summary to {output_path}")

    conn.close()

    return all_results


def get_peer_percentiles_for_company(
    company_id: str,
    year: str = "2024-03",
    db_path: str = DB_PATH
) -> pd.DataFrame:
    """Get percentile rankings for a specific company."""
    conn = sqlite3.connect(db_path)
    query = """
        SELECT peer_group_name, metric, value, percentile_rank, year
        FROM peer_percentiles
        WHERE company_id = ? AND year = ?
    """
    df = pd.read_sql(query, conn, params=[company_id, year])
    conn.close()
    return df


def get_peer_group_summary(
    peer_group_name: str,
    year: str = "2024-03",
    db_path: str = DB_PATH
) -> pd.DataFrame:
    """Get summary statistics for a peer group."""
    conn = sqlite3.connect(db_path)
    query = """
        SELECT
            metric,
            COUNT(*) as n_companies,
            AVG(value) as avg_value,
            MIN(value) as min_value,
            MAX(value) as max_value,
            AVG(percentile_rank) as avg_percentile
        FROM peer_percentiles
        WHERE peer_group_name = ? AND year = ?
        GROUP BY metric
    """
    df = pd.read_sql(query, conn, params=[peer_group_name, year])
    conn.close()
    return df


def get_companies_without_peer_group(db_path: str = DB_PATH) -> pd.DataFrame:
    """Get companies that are not assigned to any peer group."""
    conn = sqlite3.connect(db_path)
    query = """
        SELECT c.id, c.company_name, s.broad_sector
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        WHERE c.id NOT IN (SELECT DISTINCT company_id FROM peer_groups)
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Peer Percentile Engine")
    parser.add_argument("--year", type=str, default="2024-03", help="Fiscal year")
    parser.add_argument("--db-path", type=str, default=DB_PATH, help="Database path")

    args = parser.parse_args()

    compute_peer_percentiles(year=args.year, db_path=args.db_path)