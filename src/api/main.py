"""
src/api/main.py
FastAPI Server Scaffold (Day 38)
FastAPI application with SQLite connection function
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time
import sqlite3
import os
from datetime import datetime

# Import routers
from src.api.routers import (
    companies,
    screener,
    sectors,
    peers,
    valuation,
    portfolio,
    documents,
    health,
)

# Create FastAPI app
app = FastAPI(
    title="Nifty 100 Financial Intelligence Platform API",
    description="REST API for accessing financial data, ratios, screeners, and analytics for Nifty 100 companies",
    version="1.0.0",
)

# Add CORS middleware to allow all origins (internal use only)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Calculate processing time
    process_time = time.time() - start_time

    # Log request details
    print(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
    )

    return response


# Include all routers with prefix /api/v1
app.include_router(companies.router, prefix="/api/v1/companies", tags=["companies"])
app.include_router(screener.router, prefix="/api/v1/screener", tags=["screener"])
app.include_router(sectors.router, prefix="/api/v1/sectors", tags=["sectors"])
app.include_router(peers.router, prefix="/api/v1/peers", tags=["peers"])
app.include_router(valuation.router, prefix="/api/v1/valuation", tags=["valuation"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Nifty 100 Financial Intelligence Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


# Health check endpoint (also available via router)
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint returning database status and uptime"""
    start_time = time.time()

    try:
        conn = sqlite3.connect("db/nifty100.db")
        cursor = conn.cursor()

        # Get row counts for all 10 tables
        tables = [
            "companies",
            "profitandloss",
            "balancesheet",
            "cashflow",
            "analysis",
            "documents",
            "prosandcons",
            "sectors",
            "stock_prices",
            "market_cap",
            "financial_ratios",
            "peer_groups",
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
            "uptime_seconds": time.time()
            - start_time,  # Simplified - in production would track actual startup time
            "version": "1.0.0",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": time.time() - start_time,
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
