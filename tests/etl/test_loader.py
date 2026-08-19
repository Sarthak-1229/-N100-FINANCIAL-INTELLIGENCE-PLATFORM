"""
tests/etl/test_loader.py — 10 unit tests verifying loader reads correct row counts and column names for each file
"""
import pytest
import sys
import os
import sqlite3
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestLoaderRowCounts:
    """Test that loader loads correct row counts for each table"""

    def test_companies_count(self):
        """Test companies table has 92 rows"""
        conn = sqlite3.connect("db/nifty100.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM companies")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 92, f"Expected 92 companies, got {count}"

    def test_profitandloss_count(self):
        """Test profitandloss table has expected number of rows"""
        conn = sqlite3.connect("db/nifty100.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM profitandloss")
        count = cursor.fetchone()[0]
        conn.close()
        # Should have multiple rows per company (one per year)
        assert count > 92, f"Expected >92 profitandloss rows, got {count}"

    def test_balancesheet_count(self):
        """Test balancesheet table has expected number of rows"""
        conn = sqlite3.connect("db/nifty100.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM balancesheet")
        count = cursor.fetchone()[0]
        conn.close()
        assert count > 92, f"Expected >92 balancesheet rows, got {count}"

    def test_cashflow_count(self):
        """Test cashflow table has expected number of rows"""
        conn = sqlite3.connect("db/nifty100.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cashflow")
        count = cursor.fetchone()[0]
        conn.close()
        assert count > 92, f"Expected >92 cashflow rows, got {count}"

    def test_financial_ratios_count(self):
        """Test financial_ratios table has 1000+ rows"""
        conn = sqlite3.connect("db/nifty100.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM financial_ratios")
        count = cursor.fetchone()[0]
        conn.close()
        assert count >= 1000, f"Expected >=1000 financial_ratios rows, got {count}"

    def test_sectors_count(self):
        """Test sectors table has 92 rows (one per company)"""
        conn = sqlite3.connect("db/nifty100.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sectors")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 92, f"Expected 92 sector rows, got {count}"

    def test_peer_groups_count(self):
        """Test peer_groups table has data"""
        conn = sqlite3.connect("db/nifty100.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM peer_groups")
        count = cursor.fetchone()[0]
        conn.close()
        assert count > 0, f"Expected peer_groups data, got {count}"

    def test_analysis_count(self):
        """Test analysis table has data"""
        conn = sqlite3.connect("db/nifty100.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM analysis")
        count = cursor.fetchone()[0]
        conn.close()
        assert count > 0, f"Expected analysis data, got {count}"

    def test_documents_count(self):
        """Test documents table has data"""
        conn = sqlite3.connect("db/nifty100.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        count = cursor.fetchone()[0]
        conn.close()
        assert count > 0, f"Expected documents data, got {count}"

    def test_market_cap_count(self):
        """Test market_cap table has data"""
        conn = sqlite3.connect("db/nifty100.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM market_cap")
        count = cursor.fetchone()[0]
        conn.close()
        assert count > 0, f"Expected market_cap data, got {count}"


class TestLoaderColumnNames:
    """Test that tables have correct column names"""

    def test_companies_columns(self):
        """Test companies table has expected columns"""
        conn = sqlite3.connect("db/nifty100.db")
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(companies)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        expected_columns = [
            'id', 'company_name', 'company_logo', 'chart_link',
            'about_company', 'website', 'nse_profile', 'bse_profile',
            'face_value', 'book_value', 'roce_percentage', 'roe_percentage'
        ]
        for col in expected_columns:
            assert col in columns, f"Missing column {col} in companies table"

    def test_profitandloss_columns(self):
        """Test profitandloss table has expected columns"""
        conn = sqlite3.connect("db/nifty100.db")
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(profitandloss)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        expected_columns = [
            'id', 'company_id', 'year', 'sales', 'expenses',
            'operating_profit', 'opm_percentage', 'other_income',
            'interest', 'depreciation', 'profit_before_tax',
            'tax_percentage', 'net_profit', 'eps', 'dividend_payout'
        ]
        for col in expected_columns:
            assert col in columns, f"Missing column {col} in profitandloss table"

    def test_balancesheet_columns(self):
        """Test balancesheet table has expected columns"""
        conn = sqlite3.connect("db/nifty100.db")
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(balancesheet)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        expected_columns = [
            'id', 'company_id', 'year', 'equity_capital', 'reserves',
            'borrowings', 'other_liabilities', 'total_liabilities',
            'fixed_assets', 'cwip', 'investments', 'other_asset',
            'total_assets'
        ]
        for col in expected_columns:
            assert col in columns, f"Missing column {col} in balancesheet table"

    def test_cashflow_columns(self):
        """Test cashflow table has expected columns"""
        conn = sqlite3.connect("db/nifty100.db")
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(cashflow)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        expected_columns = [
            'id', 'company_id', 'year', 'operating_activity',
            'investing_activity', 'financing_activity', 'net_cash_flow'
        ]
        for col in expected_columns:
            assert col in columns, f"Missing column {col} in cashflow table"

    def test_financial_ratios_columns(self):
        """Test financial_ratios table has expected columns"""
        conn = sqlite3.connect("db/nifty100.db")
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(financial_ratios)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        expected_columns = [
            'id', 'company_id', 'year', 'net_profit_margin_pct',
            'operating_profit_margin_pct', 'return_on_equity_pct',
            'debt_to_equity', 'interest_coverage', 'asset_turnover',
            'free_cash_flow_cr', 'capex_cr', 'earnings_per_share',
            'book_value_per_share', 'dividend_payout_ratio_pct',
            'total_debt_cr', 'cash_from_operations_cr'
        ]
        for col in expected_columns:
            assert col in columns, f"Missing column {col} in financial_ratios table"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])