"""
src/api/routers/companies.py
Company Data Endpoints (Day 39)
Implements GET /api/v1/companies endpoints
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
    conn.row_factory = sqlite3.Row  # To return dict-like rows
    return conn

@router.get("/", response_model=List[dict])
async def get_companies(
    sector: Optional[str] = Query(None, description="Filter by sector"),
    market_cap_category: Optional[str] = Query(None, description="Filter by market cap category"),
    search: Optional[str] = Query(None, description="Search in company name or ticker")
):
    """
    Get list of all companies with optional filtering
    Returns: id, company_name, broad_sector, sub_sector, roe_pct, roce_pct
    """
    conn = get_db_connection()

    # Base query with latest financial data - using precomputed values from companies table
    query = """
    SELECT
        c.id,
        c.company_name,
        c.broad_sector,
        c.sub_sector,
        c.roe_percentage as roe_pct,
        c.roce_percentage as roce_pct
    FROM companies c
    WHERE 1=1
    """

    params = []

    if sector:
        query += " AND c.broad_sector = ?"
        params.append(sector)

    if market_cap_category:
        query += " AND c.market_cap_category = ?"
        params.append(market_cap_category)

    if search:
        query += " AND (c.company_name LIKE ? OR c.id LIKE ?)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term])

    query += " ORDER BY c.id"

    try:
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        # Convert to list of dicts
        result = df.to_dict('records')

        # Replace NaN with None for JSON serialization
        for record in result:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None

        return result
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}", response_model=dict)
async def get_company_profile(ticker: str):
    """
    Get full company profile for a specific ticker
    Returns: all company fields + latest year KPIs + sector data
    """
    conn = get_db_connection()

    try:
        # Get company basic info
        company_query = """
        SELECT * FROM companies WHERE id = ?
        """
        company_df = pd.read_sql_query(company_query, conn, params=[ticker])

        if company_df.empty:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Company {ticker} not found")

        company_data = company_df.iloc[0].to_dict()

        # Get latest financial ratios
        ratios_query = """
        SELECT * FROM financial_ratios
        WHERE company_id = ?
        ORDER BY year DESC
        LIMIT 1
        """
        ratios_df = pd.read_sql_query(ratios_query, conn, params=[ticker])

        if not ratios_df.empty:
            ratios_data = ratios_df.iloc[0].to_dict()
            # Merge with company data, preferring ratios data for overlapping keys
            for key, value in ratios_data.items():
                if key not in ['id', 'company_id']:  # Don't overwrite company identifiers
                    company_data[key] = value

        # Get sector info (already in company data from companies table)
        # Add any additional sector data if needed

        conn.close()

        # Replace NaN with None for JSON serialization
        for key, value in company_data.items():
            if pd.isna(value):
                company_data[key] = None

        return company_data

    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}/pl")
async def get_company_pl(
    ticker: str,
    from_year: Optional[str] = Query(None, description="Start year in YYYY-MM format"),
    to_year: Optional[str] = Query(None, description="End year in YYYY-MM format")
):
    """
    Get P&L history array for a company
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

        # Build P&L query
        query = """
        SELECT * FROM profitandloss
        WHERE company_id = ?
        """
        params = [ticker]

        if from_year:
            query += " AND year >= ?"
            params.append(from_year)

        if to_year:
            query += " AND year <= ?"
            params.append(to_year)

        query += " ORDER BY year"

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

@router.get("/{ticker}/bs")
async def get_company_bs(
    ticker: str,
    from_year: Optional[str] = Query(None, description="Start year in YYYY-MM format"),
    to_year: Optional[str] = Query(None, description="End year in YYYY-MM format")
):
    """
    Get balance sheet history array for a company
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

        # Build balance sheet query
        query = """
        SELECT * FROM balancesheet
        WHERE company_id = ?
        """
        params = [ticker]

        if from_year:
            query += " AND year >= ?"
            params.append(from_year)

        if to_year:
            query += " AND year <= ?"
            params.append(to_year)

        query += " ORDER BY year"

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

@router.get("/{ticker}/cashflow")
async def get_company_cashflow(
    ticker: str,
    from_year: Optional[str] = Query(None, description="Start year in YYYY-MM format"),
    to_year: Optional[str] = Query(None, description="End year in YYYY-MM format")
):
    """
    Get cash flow history array for a company
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

        # Build cash flow query
        query = """
        SELECT * FROM cashflow
        WHERE company_id = ?
        """
        params = [ticker]

        if from_year:
            query += " AND year >= ?"
            params.append(from_year)

        if to_year:
            query += " AND year <= ?"
            params.append(to_year)

        query += " ORDER BY year"

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

@router.get("/{ticker}/ratios")
async def get_company_ratios(
    ticker: str,
    year: Optional[str] = Query(None, description="Specific year in YYYY-MM format, defaults to latest")
):
    """
    Get all computed KPIs per year for the company
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

        # Build ratios query
        query = """
        SELECT * FROM financial_ratios
        WHERE company_id = ?
        """
        params = [ticker]

        if year:
            query += " AND year = ?"
            params.append(year)
        else:
            # If no year specified, get latest year
            query += " AND year = (SELECT MAX(year) FROM financial_ratios WHERE company_id = ?)"
            params.append(ticker)

        query += " ORDER BY year"

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

@router.get("/{ticker}/tearsheet")
async def get_company_tearsheet(ticker: str):
    """
    Get the pre-generated tearsheet PDF as a binary file download
    """
    from fastapi.responses import FileResponse

    # Check if company exists
    conn = get_db_connection()
    company_check = """
    SELECT id FROM companies WHERE id = ?
    """
    company_exists = pd.read_sql_query(company_check, conn, params=[ticker])
    conn.close()

    if company_exists.empty:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found")

    # Construct tearsheet file path
    tearsheet_path = f"reports/tearsheets/{ticker}_tearsheet.pdf"

    if not os.path.exists(tearsheet_path):
        # Return 404 if tearsheet not generated yet
        raise HTTPException(status_code=404, detail=f"Tearsheet for {ticker} not found")

    return FileResponse(
        path=tearsheet_path,
        media_type="application/pdf",
        filename=f"{ticker}_tearsheet.pdf"
    )