"""
tests/api/test_sectors.py - Tests for the sectors endpoints
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_sectors_list():
    """Test that the sectors list endpoint works"""
    response = client.get("/api/v1/sectors/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Should have 10 sectors (based on actual data)
    assert len(data) == 10

    # Check structure of sectors
    if len(data) > 0:
        sector = data[0]
        assert "sector" in sector
        assert "company_count" in sector
        assert "median_roe" in sector
        assert "median_pe" in sector
        assert "median_de" in sector


def test_sector_companies():
    """Test that we can get companies for a sector"""
    # First get the list of sectors
    response = client.get("/api/v1/sectors/")
    assert response.status_code == 200
    sectors = response.json()
    assert len(sectors) > 0

    # Get companies for the first sector - using the sector name, not id
    sector_name = sectors[0]["sector"]
    response = client.get(f"/api/v1/sectors/{sector_name}/companies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Each company should belong to the sector
    if len(data) > 0:
        company = data[0]
        assert "id" in company
        assert "company_name" in company
        assert "roe_pct" in company  # Check for actual fields returned
        # Note: We can't easily verify the sector matches without more API calls
        # but we can at least check the structure is correct


def test_sector_info():
    """Test that we can get sector information from the sectors list"""
    response = client.get("/api/v1/sectors/")
    assert response.status_code == 200
    sectors = response.json()
    assert isinstance(sectors, list)
    assert len(sectors) > 0

    # Check that each sector has the expected fields
    sector = sectors[0]
    assert "sector" in sector
    assert "company_count" in sector
    assert "median_roe" in sector
    assert "median_pe" in sector
    assert "median_de" in sector

    # Check that company_count is a positive integer
    assert isinstance(sector["company_count"], int)
    assert sector["company_count"] > 0

    # Check that median values are either numbers or null
    if sector["median_roe"] is not None:
        assert isinstance(sector["median_roe"], (int, float))
    if sector["median_pe"] is not None:
        assert isinstance(sector["median_pe"], (int, float))
    if sector["median_de"] is not None:
        assert isinstance(sector["median_de"], (int, float))