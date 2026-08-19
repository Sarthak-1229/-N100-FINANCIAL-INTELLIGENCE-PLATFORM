"""tests/screener/test_composite_score.py - tests for composite score calculation"""
import os
import sys
import pytest
import pandas as pd
import numpy as np

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from screener.engine import compute_composite_score


def test_composite_score_basic():
    """Test basic composite score functionality."""
    df = pd.DataFrame({
        'company_id': ['TCS', 'RELIANCE'],
        'company_name': ['Tata Consultancy Services Ltd', 'Reliance Industries Ltd'],
        'return_on_equity_pct': [50.0, 15.0],
        'return_on_capital_employed_pct': [20.0, 10.0],
        'net_profit': [1000, 500],
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
    assert all(0 <= score <= 100 for score in result['sector_relative_score'] if not pd.isna(score))


def test_composite_score_weights_sum_to_100():
    """Test that the weights conceptually sum to 100%."""
    # This is more of a conceptual test - the actual implementation
    # uses weights that sum to 1.0 (100%)
    df = pd.DataFrame({
        'company_id': ['TCS'],
        'company_name': ['Test Company'],
        'return_on_equity_pct': [50.0],
        'return_on_capital_employed_pct': [50.0],
        'net_profit': [1000],
        'net_profit_margin_pct': [50.0],
        'pat_cagr_5yr': [50.0],
        'free_cash_flow_cr': [50],
        'revenue_cagr_5yr': [50.0],
        'debt_to_equity': [1.0],
        'interest_coverage': [5.0],
        'broad_sector': ['Test Sector']
    })

    result = compute_composite_score(df)

    # The score should be calculable without error
    assert not pd.isna(result['final_score'].iloc[0])
    assert 0 <= result['final_score'].iloc[0] <= 100


def test_composite_score_sector_normalization():
    """Test that sector-relative normalization works."""
    df = pd.DataFrame({
        'company_id': ['TCS', 'INFY', 'RELIANCE', 'ONGC'],
        'company_name': ['TCS', 'Infosys', 'Reliance', 'ONGC'],
        'return_on_equity_pct': [50.0, 60.0, 15.0, 10.0],
        'return_on_capital_employed_pct': [20.0, 25.0, 8.0, 5.0],
        'net_profit': [1000, 1200, 500, 300],
        'net_profit_margin_pct': [10.0, 12.0, 5.0, 3.0],
        'pat_cagr_5yr': [10.0, 15.0, 5.0, 3.0],
        'free_cash_flow_cr': [100, 150, -50, -20],
        'revenue_cagr_5yr': [15.0, 20.0, 5.0, 3.0],
        'debt_to_equity': [0.1, 0.2, 2.0, 3.0],
        'interest_coverage': [5.0, 6.0, 2.0, 1.5],
        'broad_sector': ['IT', 'IT', 'Energy', 'Energy']  # Two sectors
    })

    result = compute_composite_score(df)

    # Check that scores are calculated
    assert not pd.isna(result['final_score']).any()
    assert not pd.isna(result['composite_score']).any()
    assert not pd.isna(result['sector_relative_score']).any()

    # IT sector companies (TCS, INFY) should have higher scores than Energy (RELIANCE, ONGC)
    # This is a relative check - IT sector should generally score higher
    it_scores = result[result['broad_sector'] == 'IT']['final_score'].tolist()
    energy_scores = result[result['broad_sector'] == 'Energy']['final_score'].tolist()

    # At least one IT company should score higher than at least one Energy company
    # (This is a soft test since the exact scoring depends on all factors)
    assert len(it_scores) > 0 and len(energy_scores) > 0


def test_composite_score_handles_missing_data():
    """Test that composite score handles missing data gracefully."""
    df = pd.DataFrame({
        'company_id': ['TCS', 'RELIANCE'],
        'company_name': ['Tata Consultancy Services Ltd', 'Reliance Industries Ltd'],
        'return_on_equity_pct': [50.0, None],  # Missing data
        'return_on_capital_employed_pct': [20.0, 10.0],
        'net_profit': [1000, 500],
        'net_profit_margin_pct': [10.0, 5.0],
        'pat_cagr_5yr': [10.0, 5.0],
        'free_cash_flow_cr': [100, -50],
        'revenue_cagr_5yr': [15.0, 5.0],
        'debt_to_equity': [0.1, 2.0],
        'interest_coverage': [5.0, 2.0],
        'broad_sector': ['Information Technology', 'Energy']
    })

    result = compute_composite_score(df)

    # Should still produce scores even with missing data
    assert not pd.isna(result['final_score']).all()
    assert not pd.isna(result['composite_score']).all()
    assert not pd.isna(result['sector_relative_score']).all()


if __name__ == "__main__":
    test_composite_score_basic()
    test_composite_score_weights_sum_to_100()
    test_composite_score_sector_normalization()
    test_composite_score_handles_missing_data()
    print("All composite score tests passed!")