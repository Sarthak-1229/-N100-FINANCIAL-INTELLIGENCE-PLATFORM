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
    # Should have 11 sectors as mentioned in the spec
    assert len(data) == 11

    # Check structure of sectors
    if len(data) > 0:
        sector = data[0]
        assert "id" in sector
        assert "name" in sector
        assert "broad_sector" in sector


def test_sector_companies():
    """Test that we can get companies for a sector"""
    # First get the list of sectors
    response = client.get("/api/v1/sectors/")
    assert response.status_code == 200
    sectors = response.json()
    assert len(sectors) > 0

    # Get companies for the first sector
    sector_id = sectors[0]["id"]
    response = client.get(f"/api/v1/sectors/{sector_id}/companies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Each company should belong to the sector
    if len(data) > 0:
        company = data[0]
        assert "id" in company
        assert "company_name" in company
        assert "sector" in company
        # Note: We can't easily verify the sector matches without more API calls
        # but we can at least check the structure is correct


def test_sector_info():
    """Test that we can get detailed info for a sector"""
    # Get a sector ID
    response = client.get("/api/v1/sectors/")
    sectors = response.json()
    assert len(sectors) > 0
    sector_id = sectors[0]["id"]

    response = client.get(f"/api/v1/sectors/{sector_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sector_id
    assert "name" in data
    assert "broad_sector" in data
    # Might have additional fields like median KPIs, etc.