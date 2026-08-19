"""
src/api/routers/valuation.py
Valuation Endpoints (Day 40)
Implements GET /api/v1/valuation endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import sqlite3
import pandas as pd
import os

router = APIRouter()

def get_db_connection():
    """Get SQLite database connection"""
    conn = sqlite3.connect("db/nifty100.db")
    conn.row_factory = sqlite3.Row
    return conn

@router.get("/", response_model=List[dict])
async def get_valuation_summary(
    year: Optional[str] = Query(None, description="Year in YYYY-MM format, defaults to latest")
):
    """
    Get valuation summary for all companies
    Similar to the valuation module from Sprint 4
    """
    conn = get_db_connection()

    try:
        # Determine year to use
        if year is None:
            # Get latest year
            year_query = "SELECT MAX(year) as latest_year FROM financial_ratios"
            year_df = pd.read_sql_query(year_query, conn)
            target_year = year_df.iloc[0]['latest_year']
        else:
            target_year = year

        # Query to get valuation data
        query = """
        SELECT
            c.id as company_id,
            c.company_name,
            s.broad_sector,
            fr.pe_ratio as "P/E",
            fr.pb_ratio as "P/B",
            fr.ev_ebitda as "EV/EBITDA",
            (fr.free_cash_flow_cr / mc.market_cap_crore * 100) as "FCF_yield_pct",
            mc.pe_ratio as "5yr_median_PE",
            ROUND((fr.pe_ratio / mc.pe_ratio - 1) * 100, 2) as "PE_vs_sector_median_pct",
            CASE
                WHEN fr.pe_ratio > mc.pe_ratio * 1.5 THEN 'Caution'
                WHEN fr.pe_ratio < mc.pe_ratio * 0.7 THEN 'Discount'
                ELSE 'Fair'
            END as "flag"
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        LEFT JOIN (
            SELECT
                fr.company_id,
                fr.pe_ratio,
                fr.pb_ratio,
                fr.ev_ebitda,
                fr.free_cash_flow_cr
            FROM financial_ratios fr
            WHERE fr.year = ?
        ) fr ON c.id = fr.company_id
        LEFT JOIN market_cap mc ON c.id = mc.company_id AND mc.year = ?
        LEFT JOIN (
            SELECT
                s.broad_sector,
                AVG(fr.pe_ratio) as median_pe
            FROM financial_ratios fr
            INNER JOIN sectors s ON fr.company_id = s.company_id
            WHERE fr.year = ?
            GROUP BY s.broad_sector
        ) sector_avg ON s.broad_sector = sector_avg.broad_sector
        """

        df = pd.read_sql_query(query, conn, params=[target_year, target_year, target_year])
        conn.close()

        # Rename columns for consistency
        df = df.rename(columns={
            "company_id": "company_id",
            "company_name": "company_name",
            "broad_sector": "sector",
            "P/E": "pe_ratio",
            "P/B": "pb_ratio",
            "EV/EBITDA": "ev_ebitda",
            "FCF_yield_pct": "fcf_yield_pct",
            "5yr_median_PE": "pe_ratio_5yr_median",
            "PE_vs_sector_median_pct": "pe_vs_sector_median_pct",
            "flag": "valuation_flag"
        })

        # Convert to list of dicts
        result = df.to_dict('records')

        # Replace NaN with None
        for record in result:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None

        return result
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}")
async def get_company_valuation(ticker: str, year: Optional[str] = Query(None)):
    """
    Get valuation data for a specific company
    """
    conn = get_db_connection()

    try:
        # Check if company exists
        company_check = """
        SELECT id FROM companies WHERE id = ?
        """
        company_exists = pd.read_sql_query(company_check, conn, params=[ticker])
        if company_exists.empty:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Company {ticker} not found")

        # Determine year to use
        if year is None:
            year_query = "SELECT MAX(year) as latest_year FROM financial_ratios WHERE company_id = ?"
            year_df = pd.read_sql_query(year_query, conn, params=[ticker])
            if year_df.empty:
                conn.close()
                raise HTTPException(status_code=404, detail=f"No financial data found for company {ticker}")
            target_year = year_df.iloc[0]['latest_year']
        else:
            target_year = year

        # Query similar to above but for single company
        query = """
        SELECT
            c.id as company_id,
            c.company_name,
            s.broad_sector,
            fr.pe_ratio as "P/E",
            fr.pb_ratio as "P/B",
            fr.ev_ebitda as "EV/EBITDA",
            (fr.free_cash_flow_cr / mc.market_cap_crore * 100) as "FCF_yield_pct",
            mc.pe_ratio as "5yr_median_PE",
            ROUND((fr.pe_ratio / mc.pe_ratio - 1) * 100, 2) as "PE_vs_sector_median_pct",
            CASE
                WHEN fr.pe_ratio > mc.pe_ratio * 1.5 THEN 'Caution'
                WHEN fr.pe_ratio < mc.pe_ratio * 0.7 THEN 'Discount'
                ELSE 'Fair'
            END as "flag"
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        LEFT JOIN (
            SELECT
                fr.company_id,
                fr.pe_ratio,
                fr.pb_ratio,
                fr.ev_ebitda,
                fr.free_cash_flow_cr
            FROM financial_ratios fr
            WHERE fr.company_id = ? AND fr.year = ?
        ) fr ON c.id = fr.company_id
        LEFT JOIN market_cap mc ON c.id = mc.company_id AND mc.year = ?
        LEFT JOIN (
            SELECT
                s.broad_sector,
                AVG(fr.pe_ratio) as median_pe
            FROM financial_ratios fr
            INNER JOIN sectors s ON fr.company_id = s.company_id
            WHERE fr.year = ?
            GROUP BY s.broad_sector
        ) sector_avg ON s.broad_sector = sector_avg.broad_sector
        """

        df = pd.read_sql_query(query, conn, params=[ticker, target_year, target_year, target_year, target_year])
        conn.close()

        if df.empty:
            raise HTTPException(status_code=404, detail=f"No valuation data found for company {ticker} in year {target_year}")

        # Rename columns
        df = df.rename(columns={
            "company_id": "company_id",
            "company_name": "company_name",
            "broad_sector": "sector",
            "P/E": "pe_ratio",
            "P/B": "pb_ratio",
            "EV/EBITDA": "ev_ebitda",
            "FCF_yield_pct": "fcf_yield_pct",
            "5yr_median_PE": "pe_ratio_5yr_median",
            "PE_vs_sector_median_pct": "pe_vs_sector_median_pct",
            "flag": "valuation_flag"
        })

        # Convert to dict
        result = df.to_dict('records')[0] if len(df) > 0 else {}

        # Replace NaN with None
        for key, value in result.items():
            if pd.isna(value):
                result[key] = None

        return result
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))