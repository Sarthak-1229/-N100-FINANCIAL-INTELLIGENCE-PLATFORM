"""
src/api/routers/documents.py
Documents Endpoints (Day 40)
Implements GET /api/v1/documents endpoints
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

@router.get("/{ticker}")
async def get_company_documents(ticker: str):
    """
    Get annual report links with is_url_valid boolean flag for each
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

        # Get documents (annual report links)
        query = """
        SELECT
            d.year,
            d.annual_report_url as url,
            CASE
                WHEN d.annual_report_url IS NOT NULL
                 AND d.annual_report_url LIKE 'http%'
                 AND d.annual_report_url LIKE '%.pdf'
                THEN 1
                ELSE 0
            END as is_url_valid
        FROM documents d
        WHERE d.company_id = ?
        ORDER BY d.year DESC
        """

        df = pd.read_sql_query(query, conn, params=[ticker])
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