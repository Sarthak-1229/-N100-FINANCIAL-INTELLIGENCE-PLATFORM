"""
src/analytics/correlation_heatmap.py
Generate correlation matrix heatmap: Pearson correlation of 10 KPIs across all 92 companies for latest year — save as reports/correlation_heatmap.png using matplotlib heatmap with annotation
"""

import pandas as pd
import numpy as np
import sqlite3
import os
import matplotlib.pyplot as plt

# Ensure output directories exist
os.makedirs("reports", exist_ok=True)

def get_latest_kpi_data():
    """
    Get latest year data for 10 key KPIs for correlation analysis
    Returns DataFrame with KPI columns
    """
    conn = sqlite3.connect("db/nifty100.db")

    # Get latest financial ratios data for 10 key KPIs
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

def generate_correlation_heatmap(df):
    """
    Generate correlation matrix heatmap: Pearson correlation of 10 KPIs
    Save as reports/correlation_heatmap.png using matplotlib heatmap with annotation
    """
    # Select only the KPI columns for correlation
    kpi_cols = ['return_on_equity_pct', 'debt_to_equity', 'revenue_cagr_5yr',
                'free_cash_flow_cr', 'operating_profit_margin_pct',
                'net_profit_margin_pct', 'asset_turnover', 'interest_coverage',
                'capex_intensity_pct']

    # Calculate correlation matrix
    corr_matrix = df[kpi_cols].corr(method='pearson')

    # Create heatmap using matplotlib
    fig, ax = plt.subplots(figsize=(12, 10))

    # We'll show the lower triangle (including diagonal) for clarity, but you can show full matrix
    # Create a mask for the upper triangle
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)  # Mask upper triangle without diagonal

    # Apply mask: set upper triangle to NaN for visualization (we'll still plot the lower triangle)
    corr_matrix_masked = corr_matrix.copy()
    corr_matrix_masked.where(~mask, inplace=True)  # Keep lower triangle and diagonal, set upper to NaN

    # Plot the heatmap
    im = ax.imshow(corr_matrix_masked, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')

    # Set ticks
    ax.set_xticks(np.arange(len(kpi_cols)))
    ax.set_yticks(np.arange(len(kpi_cols)))
    ax.set_xticklabels(kpi_cols, rotation=45, ha="right")
    ax.set_yticklabels(kpi_cols)

    # Loop over data dimensions and create text annotations.
    for i in range(len(kpi_cols)):
        for j in range(len(kpi_cols)):
            # Only annotate if not masked (i.e., lower triangle and diagonal)
            if not mask[i, j]:
                text = ax.text(j, i, f"{corr_matrix.iloc[i, j]:.2f}",
                               ha="center", va="center", color="black")

    # Add colorbar
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("Correlation Coefficient", rotation=-90, va="bottom")

    # Set title
    ax.set_title('Pearson Correlation Matrix of 10 Key KPIs\n(Latest Year Data)',
                 fontsize=16, fontweight='bold', pad=20)

    plt.tight_layout()

    # Save plot
    plt.savefig("reports/correlation_heatmap.png", dpi=300, bbox_inches='tight')
    plt.close()

    return corr_matrix

def main():
    """Main function to generate correlation heatmap"""
    print("Generating Correlation Matrix Heatmap (Day 37)...")

    # Step 1: Get latest KPI data
    print("1. Loading latest KPI data...")
    df = get_latest_kpi_data()
    print(f"   Loaded data for {len(df)} companies")
    print(f"   Missing values before imputation: {df.isnull().sum().sum()}")

    # Step 2: Impute missing values
    print("2. Imputing missing values with median...")
    df_imputed = impute_missing_with_median(df)
    print(f"   Missing values after imputation: {df_imputed.isnull().sum().sum()}")

    # Step 3: Generate correlation heatmap
    print("3. Generating correlation matrix heatmap...")
    corr_matrix = generate_correlation_heatmap(df_imputed)
    print(f"   Correlation heatmap saved to reports/correlation_heatmap.png")

    # Print correlation summary
    print("\n" + "="*60)
    print("CORRELATION MATRIX SUMMARY")
    print("="*60)
    print("Strongest positive correlations (|r| > 0.5):")
    strong_pos = []
    for i in range(len(corr_matrix.columns)):
        for j in range(i+1, len(corr_matrix.columns)):
            corr_val = corr_matrix.iloc[i, j]
            if abs(corr_val) > 0.5:
                strong_pos.append((corr_matrix.columns[i], corr_matrix.columns[j], corr_val))

    if strong_pos:
        for var1, var2, corr in sorted(strong_pos, key=lambda x: abs(x[2]), reverse=True):
            print(f"  {var1} ↔ {var2}: {corr:.3f}")
    else:
        print("  No strong positive correlations found (|r| > 0.5)")

    print("\nStrongest negative correlations (|r| > 0.5):")
    strong_neg = [(var1, var2, corr) for var1, var2, corr in strong_pos if corr < -0.5]
    if strong_neg:
        for var1, var2, corr in sorted(strong_neg, key=lambda x: abs(x[2]), reverse=True):
            print(f"  {var1} ↔ {var2}: {corr:.3f}")
    else:
        print("  No strong negative correlations found (|r| > 0.5)")

    print("="*60)
    print("\nCorrelation heatmap generation completed successfully!")

if __name__ == "__main__":
    main()