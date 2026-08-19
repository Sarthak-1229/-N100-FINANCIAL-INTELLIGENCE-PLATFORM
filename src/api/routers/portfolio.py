"""
src/api/routers/portfolio.py
Portfolio Endpoints (Day 40)
Implements GET /api/v1/portfolio endpoints
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
import sqlite3
import pandas as pd

router = APIRouter()

def get_db_connection():
    """Get SQLite database connection"""
    conn = sqlite3.connect("db/nifty100.db")
    conn.row_factory = sqlite3.Row
    return conn

@router.get("/stats", response_model=List[dict])
async def get_portfolio_stats():
    """
    Get P10 through P90 percentile table for 10 core KPIs across all 92 companies
    """
    conn = get_db_connection()

    try:
        # Get latest financial ratios data for key KPIs
        query = """
        SELECT
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

        df = pd.read_sql_query(query, conn)
        conn.close()

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
            # Get data for this KPI (drop NaN values)
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

        # Convert to list of dicts
        result = stats_df.to_dict('records')

        # Replace NaN with None
        for record in result:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None

        return result
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

# Import numpy for percentile calculation
import numpy as np