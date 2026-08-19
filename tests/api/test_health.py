"""
tests/api/test_health.py - Tests for the health check endpoint
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test that the health endpoint returns expected data"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "db_row_counts" in data
    assert "uptime_seconds" in data
    assert "version" in data

    # Check that we have row counts for expected tables
    expected_tables = [
        "companies", "profitandloss", "balancesheet", "cashflow",
        "financial_ratios", "sectors", "peer_groups", "analysis",
        "documents", "market_cap"
    ]

    for table in expected_tables:
        assert table in data["db_row_counts"]
        assert isinstance(data["db_row_counts"][table], int)
        assert data["db_row_counts"][table] >= 0

    # Specific checks for known data
    assert data["db_row_counts"]["companies"] == 92
    assert data["db_row_counts"]["financial_ratios"] >= 1000