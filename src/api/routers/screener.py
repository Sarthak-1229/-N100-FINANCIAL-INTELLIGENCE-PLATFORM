"""
src/api/routers/screener.py
Screener Endpoints (Day 40)
Implements GET /api/v1/screener endpoint
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
async def screen_companies(
    min_roe: Optional[float] = Query(None, description="Minimum ROE percentage"),
    max_de: Optional[float] = Query(None, description="Maximum debt-to-equity ratio"),
    min_fcf: Optional[float] = Query(None, description="Minimum free cash flow in Cr"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    min_rev_cagr_5yr: Optional[float] = Query(None, description="Minimum revenue CAGR 5yr"),
    min_pat_cagr_5yr: Optional[float] = Query(None, description="Minimum PAT CAGR 5yr"),
    max_pe: Optional[float] = Query(None, description="Maximum P/E ratio")
):
    """
    Screener endpoint with query parameters
    Returns ranked company list with all filter metrics
    """
    conn = get_db_connection()

    try:
        # Base query with latest financial data
        query = """
        SELECT
            c.id,
            c.company_name,
            s.broad_sector as sector,
            s.sub_sector,
            fr.return_on_equity_pct as roe_pct,
            fr.debt_to_equity as de_ratio,
            fr.free_cash_flow_cr as fcf_cr,
            fr.revenue_cagr_5yr as rev_cagr_5yr,
            fr.net_profit_margin_pct as npm_pct,
            fr.eps_cagr_5yr as eps_cagr_5yr,
            fr.pe_ratio as pe_ratio
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        LEFT JOIN (
            SELECT
                fr.company_id,
                fr.return_on_equity_pct,
                fr.debt_to_equity,
                fr.free_cash_flow_cr,
                fr.revenue_cagr_5yr,
                fr.net_profit_margin_pct,
                fr.eps_cagr_5yr,
                fr.pe_ratio
            FROM financial_ratios fr
            INNER JOIN (
                SELECT company_id, MAX(year) as max_year
                FROM financial_ratios
                GROUP BY company_id
            ) grouped ON fr.company_id = grouped.company_id AND fr.year = grouped.max_year
        ) fr ON c.id = fr.company_id
        WHERE 1=1
        """

        params = []

        if min_roe is not None:
            query += " AND fr.return_on_equity_pct >= ?"
            params.append(min_roe)

        if max_de is not None:
            query += " AND fr.debt_to_equity <= ?"
            params.append(max_de)

        if min_fcf is not None:
            query += " AND fr.free_cash_flow_cr >= ?"
            params.append(min_fcf)

        if sector:
            query += " AND s.broad_sector = ?"
            params.append(sector)

        if min_rev_cagr_5yr is not None:
            query += " AND fr.revenue_cagr_5yr >= ?"
            params.append(min_rev_cagr_5yr)

        if min_pat_cagr_5yr is not None:
            query += " AND fr.net_profit_margin_pct >= ?"  # Using net profit margin as proxy for PAT CAGR
            params.append(min_pat_cagr_5yr)

        if max_pe is not None:
            query += " AND fr.pe_ratio <= ?"
            params.append(max_pe)

        # Add composite score ordering (simplified)
        query += """
        ORDER BY
            CASE
                WHEN fr.return_on_equity_pct IS NOT NULL THEN fr.return_on_equity_pct
                ELSE 0
            END DESC,
            CASE
                WHEN fr.free_cash_flow_cr IS NOT NULL THEN fr.free_cash_flow_cr
                ELSE 0
            END DESC
        """

        df = pd.read_sql_query(query, conn, params=params)
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


@router.get("/presets", response_model=List[dict])
async def get_screener_presets():
    """Return a list of predefined screener presets"""
    # Return the 6 presets mentioned in the spec
    presets = [
        {
            "id": "growth_investor",
            "name": "Growth Investor",
            "description": "High revenue growth, strong ROE, moderate debt"
        },
        {
            "id": "value_investor",
            "name": "Value Investor",
            "description": "Low PE, high dividend yield, strong fundamentals"
        },
        {
            "id": "dividend_yield",
            "name": "Dividend Yield",
            "description": "Consistent dividend payers with sustainable payout ratios"
        },
        {
            "id": "quality_at_reasonable_price",
            "name": "Quality at Reasonable Price",
            "description": "Strong ROE, low debt, reasonable valuation"
        },
        {
            "id": "turnaround_opportunity",
            "name": "Turnaround Opportunity",
            "description": "Companies recovering from losses with improving fundamentals"
        },
        {
            "id": "financial_stability",
            "name": "Financial Stability",
            "description": "Low debt, strong cash flow, consistent profitability"
        }
    ]
    return presets


@router.get("/run/{preset_id}", response_model=List[dict])
async def run_preset(preset_id: str):
    """Run a screener preset - for now just returns all companies with no filters"""
    # In a real implementation, we would map preset_id to specific filter values
    # For now, we just call screen_companies with no filters
    return await screen_companies(
        min_roe=None,
        max_de=None,
        min_fcf=None,
        sector=None,
        min_rev_cagr_5yr=None,
        min_pat_cagr_5yr=None,
        max_pe=None
    )


@router.post("/custom", response_model=List[dict])
async def run_custom(filters: dict):
    """Run a screener with custom filters - for now just returns all companies with no filters"""
    # In a real implementation, we would extract filter values from the dict
    # For now, we just call screen_companies with no filters
    return await screen_companies()