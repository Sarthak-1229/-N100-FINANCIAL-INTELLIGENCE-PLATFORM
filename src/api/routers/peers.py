"""
src/api/routers/peers.py
Peer Endpoints (Day 40)
Implements GET /api/v1/peers endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import sqlite3
import pandas as pd

router = APIRouter()

def get_db_connection():
    """Get SQLite database connection"""
    conn = sqlite3.connect("db/nifty100.db")
    conn.row_factory = sqlite3.Row
    return conn

@router.get("/", response_model=List[dict])
async def get_peer_groups():
    """
    Get all peer groups
    """
    conn = get_db_connection()

    try:
        query = """
        SELECT DISTINCT peer_group_name as group_name
        FROM peer_groups
        ORDER BY peer_group_name
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        result = df.to_dict('records')
        for record in result:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
        return result
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{group_name}", response_model=List[dict])
async def get_peer_group_companies(group_name: str):
    """
    Get all companies in a peer group with percentile rank for each of 10 metrics
    """
    conn = get_db_connection()

    try:
        # Check if peer group exists
        group_check = """
        SELECT DISTINCT peer_group_name FROM peer_groups WHERE peer_group_name = ?
        """
        group_exists = pd.read_sql_query(group_check, conn, params=[group_name])
        if group_exists.empty:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Peer group {group_name} not found")

        # Get companies in peer group with percentile ranks
        # We need to compute percentiles for each metric across all companies, then assign to each company in the group
        # For simplicity, we'll return the companies with their latest year metrics and precomputed percentile ranks if available
        # Alternatively, we can compute on the fly.

        # First, get latest year data for all companies for the 10 metrics
        metrics_query = """
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

        all_metrics = pd.read_sql_query(metrics_query, conn)

        # Get companies in the peer group
        group_companies_query = """
        SELECT
            pg.company_id,
            c.company_name,
            c.broad_sector
        FROM peer_groups pg
        INNER JOIN companies c ON pg.company_id = c.id
        WHERE pg.peer_group_name = ?
        """
        group_companies = pd.read_sql_query(group_companies_query, conn, params=[group_name])

        if group_companies.empty:
            conn.close()
            raise HTTPException(status_code=404, detail=f"No companies found in peer group {group_name}")

        # Merge to get metrics for these companies
        company_metrics = group_companies.merge(all_metrics, on="company_id", how="left")

        # For each metric, compute percentile rank (using scipy or manual)
        # We'll compute percentile rank as the percentage of companies with value less than or equal to the company's value
        metric_cols = ['return_on_equity_pct', 'debt_to_equity', 'revenue_cagr_5yr',
                       'free_cash_flow_cr', 'operating_profit_margin_pct',
                       'net_profit_margin_pct', 'asset_turnover', 'interest_coverage',
                       'capex_intensity_pct']

        for col in metric_cols:
            # Get all values for this metric (excluding NaN)
            all_vals = all_metrics[col].dropna().values
            if len(all_vals) > 0:
                # Compute percentile rank for each company
                def percentile_rank(val):
                    if pd.isna(val):
                        return None
                    # Percentage of values in all_vals that are <= val
                    return (np.sum(all_vals <= val) / len(all_vals)) * 100
                company_metrics[f'{col}_percentile'] = company_metrics[col].apply(percentile_rank)
            else:
                company_metrics[f'{col}_percentile'] = None

        conn.close()

        # Select columns to return
        result_cols = ['company_id', 'company_name', 'broad_sector'] + \
                      [f'{col}_percentile' for col in metric_cols]
        result_df = company_metrics[result_cols]

        # Convert to list of dicts
        result = result_df.to_dict('records')

        # Replace NaN with None
        for record in result:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None

        return result
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

# Need to import numpy for percentile calculation
import numpy as np