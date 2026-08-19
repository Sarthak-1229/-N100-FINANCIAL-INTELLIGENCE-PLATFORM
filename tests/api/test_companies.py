"""
tests/api/test_companies.py - Tests for the companies endpoints
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_companies_list():
    """Test that the companies list endpoint returns data"""
    response = client.get("/api/v1/companies/")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 92  # Should have 92 companies

    # Check structure of first company
    if len(data) > 0:
        company = data[0]
        assert "id" in company
        assert "company_name" in company
        assert "sector" in company


def test_company_profile():
    """Test that the company profile endpoint works"""
    # First get a company ID from the list
    response = client.get("/api/v1/companies/")
    assert response.status_code == 200
    companies = response.json()
    assert len(companies) > 0

    company_id = companies[0]["id"]

    # Get the profile for this company
    response = client.get(f"/api/v1/companies/{company_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == company_id
    assert "company_name" in data
    assert "sector" in data
    assert "about_company" in data


def test_company_financials():
    """Test that company financials endpoints work"""
    # Get a company ID
    response = client.get("/api/v1/companies/")
    companies = response.json()
    company_id = companies[0]["id"]

    # Test P&L
    response = client.get(f"/api/v1/companies/{company_id}/profitandloss")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Test Balance Sheet
    response = client.get(f"/api/v1/companies/{company_id}/balancesheet")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Test Cash Flow
    response = client.get(f"/api/v1/companies/{company_id}/cashflow")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_company_ratios():
    """Test that company ratios endpoint works"""
    # Get a company ID
    response = client.get("/api/v1/companies/")
    companies = response.json()
    company_id = companies[0]["id"]

    response = client.get(f"/api/v1/companies/{company_id}/ratios")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)

    # Check for expected ratio fields
    expected_ratios = [
        "net_profit_margin_pct", "operating_profit_margin_pct",
        "return_on_equity_pct", "debt_to_equity", "interest_coverage"
    ]
    for ratio in expected_ratios:
        assert ratio in data


def test_company_tearsheet():
    """Test that company tearsheet endpoint works"""
    # Get a company ID
    response = client.get("/api/v1/companies/")
    companies = response.json()
    company_id = companies[0]["id"]

    response = client.get(f"/api/v1/companies/{company_id}/tearsheet")
    # This might return a PDF or redirect, so we check for success
    assert response.status_code == 200
    # For PDF, content-type would be application/pdf
    # We'll just check that we got a response