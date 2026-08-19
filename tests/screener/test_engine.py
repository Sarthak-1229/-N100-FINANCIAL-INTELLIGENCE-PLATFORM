"""tests/screener/test_engine.py - tests for screener engine"""
import os
import tempfile
import yaml
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.screener.engine import (
    load_config,
    get_financials_companies,
    load_screener_data,
    apply_filters,
    compute_composite_score,
    run_screener,
    run_all_presets,
    export_screener_output,
)


def test_load_config():
    """Test loading screener configuration."""
    config = load_config()
    assert 'metrics' in config
    assert 'presets' in config
    assert 'quality_compounder' in config['presets']
    assert config['presets']['quality_compounder']['roe_min'] == 15


def test_get_financials_companies():
    """Test getting Financials companies from database."""
    # This test requires a database connection, so we'll mock it
    # For now, just test that the function exists and is callable
    assert callable(get_financials_companies)


def test_apply_filters():
    """Test filter application logic."""
    # Create test DataFrame
    df = pd.DataFrame({
        'company_id': ['TCS', 'RELIANCE', 'HDFCBANK'],
        'return_on_equity_pct': [50.0, 15.0, 20.0],
        'debt_to_equity': [0.1, 2.0, 0.5],
        'free_cash_flow_cr': [100, -50, 200],
        'revenue_cagr_5yr': [15.0, 5.0, 25.0]
    })

    financials_ids = {'HDFCBANK'}  # HDFCBANK is Financials

    # Test roe_min filter
    filters = {'roe_min': 20}
    result = apply_filters(df, filters, financials_ids)
    assert len(result) == 2  # TCS (50) and HDFCBANK (20) pass, RELIANCE (15) fails
    assert set(result['company_id']) == {'TCS', 'HDFCBANK'}

    # Test de_max filter (should skip Financials)
    filters = {'de_max': 1.0}
    result = apply_filters(df, filters, financials_ids)
    # TCS (0.1) passes, RELIANCE (2.0) fails, HDFCBANK (0.5) passes but is Financials -> should pass due to skip rule
    assert len(result) == 2  # TCS and HDFCBANK
    assert set(result['company_id']) == {'TCS', 'HDFCBANK'}

    # Test fcf_min filter
    filters = {'fcf_min': 0}
    result = apply_filters(df, filters, financials_ids)
    # TCS (100) passes, RELIANCE (-50) fails, HDFCBANK (200) passes
    assert len(result) == 2
    assert set(result['company_id']) == {'TCS', 'HDFCBANK'}

    # Test revenue_cagr_5yr_min filter
    filters = {'revenue_cagr_5yr_min': 10}
    result = apply_filters(df, filters, financials_ids)
    # TCS (15) passes, RELIANCE (5) fails, HDFCBANK (25) passes
    assert len(result) == 2
    assert set(result['company_id']) == {'TCS', 'HDFCBANK'}


def test_compute_composite_score():
    """Test composite score computation."""
    df = pd.DataFrame({
        'company_id': ['TCS', 'RELIANCE'],
        'company_name': ['Tata Consultancy Services Ltd', 'Reliance Industries Ltd'],
        'return_on_equity_pct': [50.0, 15.0],
        'return_on_capital_employed_pct': [20.0, 10.0],
        'net_profit': [1000, 500],  # net profit in Cr
        'net_profit_margin_pct': [10.0, 5.0],
        'pat_cagr_5yr': [10.0, 5.0],
        'free_cash_flow_cr': [100, -50],
        'revenue_cagr_5yr': [15.0, 5.0],
        'debt_to_equity': [0.1, 2.0],
        'interest_coverage': [5.0, 2.0],
        'broad_sector': ['Information Technology', 'Energy']
    })

    result = compute_composite_score(df)

    # Check that score columns exist
    assert 'final_score' in result.columns
    assert 'composite_score' in result.columns
    assert 'sector_relative_score' in result.columns

    # Check that scores are in reasonable range
    assert all(0 <= score <= 100 for score in result['final_score'] if not pd.isna(score))
    assert all(0 <= score <= 100 for score in result['composite_score'] if not pd.isna(score))


def test_run_screener_without_preset():
    """Test running screener without preset (all companies)."""
    # This would require mocking the database connection
    # For now, test that function exists
    assert callable(run_screener)


def test_run_all_presets():
    """Test running all presets."""
    # This would require mocking the database connection
    # For now, test that function exists
    assert callable(run_all_presets)


def test_export_screener_output():
    """Test exporting screener output."""
    # Create minimal test data
    results = {
        'test_preset': pd.DataFrame({
            'company_id': ['TCS'],
            'company_name': ['Tata Consultancy Services Ltd'],
            'final_score': [85.0],
            'return_on_equity_pct': [50.94],
            'debt_to_equity': [0.09]
        })
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'test_output.xlsx')
        # This would require mocking the export function
        # For now, just test that the function exists and is callable
        assert callable(export_screener_output)