"""
src/analytics/outlier_detection.py
Outlier detection: compute Z-score for each metric per broad_sector — flag companies where any metric has absolute Z-score > 3 — save to output/outlier_report.csv
"""

import pandas as pd
import numpy as np
import sqlite3
import os
from scipy import stats

# Ensure output directory exists
os.makedirs("output", exist_ok=True)

def get_data_for_outlier_detection():
    """
    Get data for outlier detection: company financial metrics + sector information
    Returns DataFrame with company_id, sector, and metrics
    """
    conn = sqlite3.connect("db/nifty100.db")

    # Get latest financial ratios data for key metrics
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

    # Get sector data
    sectors_df = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
    conn.close()

    # Merge sector data
    df_with_sector = df.merge(sectors_df, on="company_id", how="left")

    return df_with_sector

def detect_outliers_zscore(df, threshold=3):
    """
    Detect outliers using Z-score method per sector for each metric
    Returns DataFrame with outlier flags
    """
    # Metrics to check for outliers
    metric_cols = ['return_on_equity_pct', 'debt_to_equity', 'revenue_cagr_5yr',
                   'free_cash_flow_cr', 'operating_profit_margin_pct',
                   'net_profit_margin_pct', 'asset_turnover', 'interest_coverage',
                   'capex_intensity_pct']

    # Create a copy to avoid modifying original data
    df_out = df.copy()

    # Initialize outlier columns
    for col in metric_cols:
        df_out[f'{col}_outlier'] = False
        df_out[f'{col}_zscore'] = np.nan

    # Get sector data from companies and sectors tables if not already in df
    # Check if broad_sector column exists, if not, we need to join it
    if 'broad_sector' not in df.columns:
        conn = sqlite3.connect("db/nifty100.db")
        sectors_df = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
        conn.close()
        df = df.merge(sectors_df, on="company_id", how="left")

    # Process each sector separately
    sectors = df['broad_sector'].dropna().unique()
    outlier_records = []

    for sector in sectors:
        if pd.isna(sector):
            continue

        sector_mask = df['broad_sector'] == sector
        sector_data = df[sector_mask]

        if len(sector_data) < 2:  # Need at least 2 samples for meaningful Z-score
            continue

        # Calculate Z-scores for each metric in this sector
        for col in metric_cols:
            if col in sector_data.columns:
                # Extract values for this sector and metric
                values = sector_data[col].dropna()

                if len(values) > 0:
                    mean_val = values.mean()
                    std_val = values.std()

                    # Avoid division by zero
                    if std_val > 0:
                        # Calculate Z-scores for all values in this sector
                        z_scores = (sector_data[col] - mean_val) / std_val

                        # Store Z-scores
                        df_out.loc[sector_mask, f'{col}_zscore'] = z_scores

                        # Flag outliers (absolute Z-score > threshold)
                        outlier_mask = np.abs(z_scores) > threshold
                        df_out.loc[sector_mask, f'{col}_outlier'] = outlier_mask

                        # Record outlier details
                        outlier_indices = sector_data.index[outlier_mask]
                        for idx in outlier_indices:
                            company_id = df.loc[idx, 'company_id']
                            outlier_value = df.loc[idx, col]
                            z_score = z_scores.loc[idx]

                            outlier_records.append({
                                'company_id': company_id,
                                'sector': sector,
                                'metric': col,
                                'value': outlier_value,
                                'z_score': z_score,
                                'sector_mean': mean_val,
                                'sector_std': std_val
                            })

    # Create outlier summary DataFrame
    outlier_df = pd.DataFrame(outlier_records) if outlier_records else pd.DataFrame(columns=[
        'company_id', 'sector', 'metric', 'value', 'z_score', 'sector_mean', 'sector_std'
    ])

    # Create summary of companies with any outliers
    companies_with_outliers = df_out.copy()
    outlier_cols = [f'{col}_outlier' for col in metric_cols]
    companies_with_outliers['any_outlier'] = companies_with_outliers[outlier_cols].any(axis=1)

    outlier_summary = companies_with_outliers[companies_with_outliers['any_outlier']][['company_id', 'broad_sector'] + outlier_cols].copy()
    outlier_summary = outlier_summary.rename(columns={'broad_sector': 'sector'})

    return outlier_df, outlier_summary

def main():
    """Main function to run outlier detection"""
    print("Starting Outlier Detection (Day 37)...")

    # Step 1: Get data
    print("1. Loading financial data with sector information...")
    df = get_data_for_outlier_detection()
    print(f"   Loaded data for {len(df)} companies")

    # Check for missing values
    metric_cols = ['return_on_equity_pct', 'debt_to_equity', 'revenue_cagr_5yr',
                   'free_cash_flow_cr', 'operating_profit_margin_pct',
                   'net_profit_margin_pct', 'asset_turnover', 'interest_coverage',
                   'capex_intensity_pct']
    missing_counts = df[metric_cols].isnull().sum()
    print(f"   Missing values per metric:")
    for col, count in missing_counts.items():
        if count > 0:
            print(f"     {col}: {count}")

    # Step 2: Detect outliers
    print("2. Detecting outliers using Z-score method (threshold=3) per sector...")
    outlier_details, outlier_summary = detect_outliers_zscore(df, threshold=3)

    # Step 3: Save results
    print("3. Saving outlier reports...")

    # Save detailed outlier records
    if not outlier_details.empty:
        outlier_details.to_csv("output/outlier_report.csv", index=False)
        print(f"   Detailed outlier report saved to output/outlier_report.csv ({len(outlier_details)} outliers)")
    else:
        # Create empty file with headers
        pd.DataFrame(columns=['company_id', 'sector', 'metric', 'value', 'z_score', 'sector_mean', 'sector_std']).to_csv("output/outlier_report.csv", index=False)
        print("   No outliers found. Created empty output/outlier_report.csv")

    # Save summary of companies with outliers
    outlier_summary.to_csv("output/companies_with_outliers.csv", index=False)
    print(f"   Companies with outliers summary saved to output/companies_with_outliers.csv ({len(outlier_summary)} companies)")

    # Print summary statistics
    print("\n" + "="*60)
    print("OUTLIER DETECTION SUMMARY")
    print("="*60)
    print(f"Total companies analyzed: {len(df)}")
    print(f"Companies with at least one outlier: {len(outlier_summary)}")
    print(f"Percentage of companies with outliers: {len(outlier_summary)/len(df)*100:.1f}%")

    if not outlier_details.empty:
        print(f"\nTotal outlier instances: {len(outlier_details)}")
        print("\nOutliers by metric:")
        metric_counts = outlier_details['metric'].value_counts()
        for metric, count in metric_counts.items():
            print(f"  {metric}: {count}")

        print("\nOutliers by sector:")
        sector_counts = outlier_details['sector'].value_counts()
        for sector, count in sector_counts.items():
            print(f"  {sector}: {count}")

        print("\nMost extreme outliers (|Z-score| > 5):")
        extreme_outliers = outlier_details[np.abs(outlier_details['z_score']) > 5]
        if not extreme_outliers.empty:
            for _, row in extreme_outliers.iterrows():
                print(f"  {row['company_id']} ({row['sector']}): {row['metric']} = {row['value']:.2f} (Z-score = {row['z_score']:.2f})")
        else:
            print("  No extreme outliers (|Z-score| > 5) found")

    print("="*60)
    print("\nOutlier detection completed successfully!")

if __name__ == "__main__":
    main()