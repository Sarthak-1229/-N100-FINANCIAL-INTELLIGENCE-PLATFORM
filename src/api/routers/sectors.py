"""
src/api/routers/sectors.py
Sector Endpoints (Day 40)
Implements GET /api/v1/sectors endpoints
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
async def get_sectors():
    """
    Get all sectors with company count, median ROE, median PE, median DE
    """
    conn = get_db_connection()

    try:
        # Query to get sector statistics
        query = """
        SELECT
            s.broad_sector as sector,
            COUNT(c.id) as company_count,
            ROUND(AVG(fr.return_on_equity_pct), 2) as median_roe,
            ROUND(AVG(fr.pe_ratio), 2) as median_pe,
            ROUND(AVG(fr.debt_to_equity), 2) as median_de
        FROM sectors s
        LEFT JOIN companies c ON s.company_id = c.id
        LEFT JOIN (
            SELECT
                fr.company_id,
                fr.return_on_equity_pct,
                fr.pe_ratio,
                fr.debt_to_equity
            FROM financial_ratios fr
            INNER JOIN (
                SELECT company_id, MAX(year) as max_year
                FROM financial_ratios
                GROUP BY company_id
            ) grouped ON fr.company_id = grouped.company_id AND fr.year = grouped.max_year
        ) fr ON c.id = fr.company_id
        GROUP BY s.broad_sector
        ORDER BY s.broad_sector
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

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

@router.get("/{sector}/companies", response_model=List[dict])
async def get_sector_companies(sector: str):
    """
    Get all companies in a sector with latest year KPIs
    """
    conn = get_db_connection()

    try:
        # Check if sector exists
        sector_check = """
        SELECT DISTINCT broad_sector FROM sectors WHERE broad_sector = ?
        """
        sector_exists = pd.read_sql_query(sector_check, conn, params=[sector])
        if sector_exists.empty:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Sector {sector} not found")

        # Get companies in sector with latest KPIs
        query = """
        SELECT
            c.id,
            c.company_name,
            fr.return_on_equity_pct as roe_pct,
            fr.debt_to_equity as de_ratio,
            fr.net_profit_margin_pct as npm_pct,
            fr.free_cash_flow_cr as fcf_cr,
            fr.revenue_cagr_5yr as rev_cagr_5yr,
            fr.operating_profit_margin_pct as opm_pct
        FROM companies c
        INNER JOIN sectors s ON c.id = s.company_id
        LEFT JOIN (
            SELECT
                fr.company_id,
                fr.return_on_equity_pct,
                fr.debt_to_equity,
                fr.net_profit_margin_pct,
                fr.free_cash_flow_cr,
                fr.revenue_cagr_5yr,
                fr.operating_profit_margin_pct
            FROM financial_ratios fr
            INNER JOIN (
                SELECT company_id, MAX(year) as max_year
                FROM financial_ratios
                GROUP BY company_id
            ) grouped ON fr.company_id = grouped.company_id AND fr.year = grouped.max_year
        ) fr ON c.id = fr.company_id
        WHERE s.broad_sector = ?
        ORDER BY c.id
        """

        df = pd.read_sql_query(query, conn, params=[sector])
        conn.close()

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