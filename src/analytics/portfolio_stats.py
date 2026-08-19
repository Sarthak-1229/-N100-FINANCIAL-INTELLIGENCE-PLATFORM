"""
src/analytics/portfolio_stats.py
Generate portfolio statistics: P10, P25, P50, P75, P90, Mean, Std for each KPI across all 92 companies
Save to output/portfolio_stats.csv
"""

import pandas as pd
import numpy as np
import sqlite3
import os

# Ensure output directory exists
os.makedirs("output", exist_ok=True)

def get_latest_kpi_data():
    """
    Get latest year data for key KPIs for portfolio statistics
    Returns DataFrame with KPI columns
    """
    conn = sqlite3.connect("db/nifty100.db")

    # Get latest financial ratios data for key KPIs
    query = """
    SELECT
        fr.company_id,
        fr.return_on_equity_pct,
        fr.debt_to_equity,
        fr.revenue_cagr_5yr,
        fr.free_cash_flow_cr,
        fr.operating_profit_margin_pct,
        fr.net_profit_margin_pct,
        fr.asset_turnover,
        fr.interest_coverage,
        fr.capex_intensity_pct
    FROM financial_ratios fr
    INNER JOIN (
        SELECT company_id, MAX(year) as max_year
        FROM financial_ratios
        GROUP BY company_id
    ) grouped ON fr.company_id = grouped.company_id AND fr.year = grouped.max_year
    """

    df = pd.read_sql(query, conn)
    conn.close()
    return df

def impute_missing_with_median(df):
    """
    Impute missing values with median for each KPI
    Returns DataFrame with imputed values
    """
    # KPI columns to impute
    kpi_cols = ['return_on_equity_pct', 'debt_to_equity', 'revenue_cagr_5yr',
                'free_cash_flow_cr', 'operating_profit_margin_pct',
                'net_profit_margin_pct', 'asset_turnover', 'interest_coverage',
                'capex_intensity_pct']

    # Impute missing values with median for each KPI
    df_imputed = df.copy()
    for col in kpi_cols:
        if df_imputed[col].isnull().any():
            median_val = df_imputed[col].median()
            df_imputed[col] = df_imputed[col].fillna(median_val)

    return df_imputed

def calculate_portfolio_statistics(df):
    """
    Calculate P10, P25, P50, P75, P90, Mean, Std for each KPI
    Returns DataFrame with statistics
    """
    # KPI columns to analyze
    kpi_cols = ['return_on_equity_pct', 'debt_to_equity', 'revenue_cagr_5yr',
                'free_cash_flow_cr', 'operating_profit_margin_pct',
                'net_profit_margin_pct', 'asset_turnover', 'interest_coverage',
                'capex_intensity_pct']

    # Statistics to calculate
    stats_cols = ['P10', 'P25', 'P50', 'P75', 'P90', 'Mean', 'Std']

    # Create results DataFrame
    results = []

    for col in kpi_cols:
        # Get data for this KPI (should have no missing values after imputation)
        data = df[col].dropna()

        if len(data) > 0:
            # Calculate statistics
            p10 = np.percentile(data, 10)
            p25 = np.percentile(data, 25)
            p50 = np.percentile(data, 50)  # Median
            p75 = np.percentile(data, 75)
            p90 = np.percentile(data, 90)
            mean_val = np.mean(data)
            std_val = np.std(data)

            results.append({
                'KPI': col,
                'P10': round(p10, 4),
                'P25': round(p25, 4),
                'P50': round(p50, 4),
                'P75': round(p75, 4),
                'P90': round(p90, 4),
                'Mean': round(mean_val, 4),
                'Std': round(std_val, 4)
            })
        else:
            # No data available
            results.append({
                'KPI': col,
                'P10': None,
                'P25': None,
                'P50': None,
                'P75': None,
                'P90': None,
                'Mean': None,
                'Std': None
            })

    # Create DataFrame
    stats_df = pd.DataFrame(results)
    return stats_df

def main():
    """Main function to generate portfolio statistics"""
    print("Generating Portfolio Statistics (Day 37)...")

    # Step 1: Get latest KPI data
    print("1. Loading latest KPI data...")
    df = get_latest_kpi_data()
    print(f"   Loaded data for {len(df)} companies")
    print(f"   Missing values before imputation: {df.isnull().sum().sum()}")

    # Step 2: Impute missing values
    print("2. Imputing missing values with median...")
    df_imputed = impute_missing_with_median(df)
    print(f"   Missing values after imputation: {df_imputed.isnull().sum().sum()}")

    # Step 3: Calculate portfolio statistics
    print("3. Calculating portfolio statistics (P10, P25, P50, P75, P90, Mean, Std)...")
    stats_df = calculate_portfolio_statistics(df_imputed)

    # Step 4: Save results
    print("4. Saving portfolio statistics...")
    stats_df.to_csv("output/portfolio_stats.csv", index=False)
    print(f"   Portfolio statistics saved to output/portfolio_stats.csv")

    # Print summary
    print("\n" + "="*60)
    print("PORTFOLIO STATISTICS SUMMARY")
    print("="*60)
    print(stats_df.to_string(index=False))
    print("="*60)
    print("\nPortfolio statistics generation completed successfully!")

if __name__ == "__main__":
    main()