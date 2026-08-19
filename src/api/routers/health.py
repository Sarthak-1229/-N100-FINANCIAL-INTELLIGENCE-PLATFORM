"""
src/api/routers/health.py
Health Endpoints (Day 38)
Implements GET /api/v1/health endpoint
"""

from fastapi import APIRouter
import time
import sqlite3
import pandas as pd
from datetime import datetime

router = APIRouter()

# Track startup time
startup_time = time.time()

@router.get("/", response_model=dict)
async def health_check():
    """
    Health check endpoint returning database status and uptime
    Returns: status=ok, db_row_counts for all 10 tables, uptime_seconds, version string
    """
    start_time = time.time()

    try:
        conn = sqlite3.connect("db/nifty100.db")
        cursor = conn.cursor()

        # Get row counts for all 12 tables
        tables = [
            "companies", "profitandloss", "balancesheet", "cashflow",
            "analysis", "documents", "prosandcons", "sectors",
            "stock_prices", "market_cap", "financial_ratios", "peer_groups"
        ]

        db_row_counts = {}
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                db_row_counts[table] = count
            except sqlite3.Error as e:
                db_row_counts[table] = f"Error: {e}"

        conn.close()

        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "db_row_counts": db_row_counts,
            "uptime_seconds": round(time.time() - startup_time, 2),
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": round(time.time() - startup_time, 2)
        }

@router.get("/version")
async def get_version():
    """
    Get API version information
    """
    return {
        "version": "1.0.0",
        "name": "Nifty 100 Financial Intelligence Platform API",
        "description": "REST API for financial data, ratios, screeners, and analytics"
    }