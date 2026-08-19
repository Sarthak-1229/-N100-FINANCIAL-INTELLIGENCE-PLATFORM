"""tests/kpi/test_ratios.py — 16+ tests for profitability, leverage, efficiency ratios"""
import pytest
from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
    debt_to_equity,
    interest_coverage,
    net_debt,
    asset_turnover,
)


class TestNetProfitMargin:
    """NPM = net_profit / sales * 100"""

    def test_normal_case(self):
        assert net_profit_margin(100, 1000) == 10.0

    def test_zero_sales_returns_none(self):
        assert net_profit_margin(100, 0) is None

    def test_none_sales_returns_none(self):
        assert net_profit_margin(100, None) is None

    def test_none_net_profit_returns_none(self):
        assert net_profit_margin(None, 1000) is None

    def test_negative_sales_returns_none(self):
        assert net_profit_margin(100, -500) is None


class TestOperatingProfitMargin:
    """OPM = operating_profit / sales * 100 (with cross-check)"""

    def test_normal_case(self):
        opm, mismatch = operating_profit_margin(200, 1000)
        assert opm == 20.0
        assert mismatch is False

    def test_cross_check_mismatch_flag(self):
        # Source OPM 30%, computed 20% -> mismatch > 1%
        opm, mismatch = operating_profit_margin(200, 1000, opm_percentage=30.0)
        assert opm == 20.0
        assert mismatch is True

    def test_cross_check_within_tolerance(self):
        # Source OPM 20.5%, computed 20% -> within 1%
        opm, mismatch = operating_profit_margin(200, 1000, opm_percentage=20.5)
        assert opm == 20.0
        assert mismatch is False

    def test_zero_sales_returns_none(self):
        opm, mismatch = operating_profit_margin(200, 0)
        assert opm is None
        assert mismatch is False

    def test_none_operating_profit_returns_none(self):
        opm, mismatch = operating_profit_margin(None, 1000)
        assert opm is None
        assert mismatch is False

    def test_none_opm_percentage_no_crash(self):
        opm, mismatch = operating_profit_margin(200, 1000, opm_percentage=None)
        assert opm == 20.0
        assert mismatch is False


class TestReturnOnEquity:
    """ROE = net_profit / (equity_capital + reserves) * 100"""

    def test_normal_case(self):
        assert return_on_equity(100, 500, 500) == 10.0

    def test_negative_equity_returns_none(self):
        assert return_on_equity(100, -200, 100) is None  # equity+reserves = -100

    def test_zero_equity_returns_none(self):
        assert return_on_equity(100, 0, 0) is None

    def test_none_inputs_return_none(self):
        assert return_on_equity(None, 500, 500) is None
        assert return_on_equity(100, None, 500) is None
        assert return_on_equity(100, 500, None) is None

    def test_reserves_only(self):
        # equity_capital=0, reserves=1000
        assert return_on_equity(150, 0, 1000) == 15.0


class TestReturnOnCapitalEmployed:
    """ROCE = EBIT / (equity + reserves + borrowings) * 100
       Financials: net_profit / total_assets * 100"""

    def test_normal_case_non_financial(self):
        # EBIT = 200 - 50 = 150, Capital = 500+500+300 = 1300
        roce = return_on_capital_employed(200, 50, 500, 500, 300, 2000, is_financial=False)
        assert roce == round((150 / 1300) * 100, 2)

    def test_financial_uses_roa_proxy(self):
        # For financials, uses net_profit / total_assets
        # operating_profit acts as net_profit proxy here
        roce = return_on_capital_employed(100, 0, 500, 500, 5000, 2000, is_financial=True)
        assert roce == round((100 / 2000) * 100, 2)

    def test_zero_capital_employed_returns_none(self):
        roce = return_on_capital_employed(200, 50, 0, 0, 0, 2000, is_financial=False)
        assert roce is None

    def test_financial_zero_assets_returns_none(self):
        roce = return_on_capital_employed(100, 0, 500, 500, 5000, 0, is_financial=True)
        assert roce is None

    def test_none_inputs_return_none(self):
        roce = return_on_capital_employed(None, 50, 500, 500, 300, 2000, is_financial=False)
        assert roce is None


class TestReturnOnAssets:
    """ROA = net_profit / total_assets * 100"""

    def test_normal_case(self):
        assert return_on_assets(100, 2000) == 5.0

    def test_zero_assets_returns_none(self):
        assert return_on_assets(100, 0) is None

    def test_negative_assets_returns_none(self):
        assert return_on_assets(100, -500) is None

    def test_none_inputs_return_none(self):
        assert return_on_assets(None, 2000) is None
        assert return_on_assets(100, None) is None


class TestDebtToEquity:
    """D/E = borrowings / (equity + reserves) — return 0 if borrowings=0"""

    def test_normal_case(self):
        de, flag = debt_to_equity(500, 500, 500, is_financial=False)
        assert de == 0.5
        assert flag is False

    def test_debt_free_returns_zero(self):
        de, flag = debt_to_equity(0, 500, 500, is_financial=False)
        assert de == 0.0
        assert flag is False

    def test_high_leverage_flag_non_financial(self):
        # D/E = 1000/100 = 10 > 5, non-financial -> flag=True
        de, flag = debt_to_equity(1000, 50, 50, is_financial=False)
        assert de == 10.0
        assert flag is True

    def test_high_leverage_no_flag_for_financial(self):
        # D/E = 10 > 5, but financial -> flag=False
        de, flag = debt_to_equity(1000, 50, 50, is_financial=True)
        assert de == 10.0
        assert flag is False

    def test_negative_equity_returns_none(self):
        de, flag = debt_to_equity(500, -200, -200, is_financial=False)
        assert de is None
        assert flag is False

    def test_none_borrowings_treated_as_zero(self):
        de, flag = debt_to_equity(None, 500, 500, is_financial=False)
        assert de == 0.0
        assert flag is False


class TestInterestCoverage:
    """ICR = (operating_profit + other_income) / interest
       Returns None + 'Debt Free' label if interest=0"""

    def test_normal_case(self):
        icr, label, flag = interest_coverage(200, 50, 50)
        assert icr == 5.0
        assert label is None
        assert flag is False

    def test_low_icr_flag(self):
        # ICR = (100+0)/100 = 1.0 < 1.5
        icr, label, flag = interest_coverage(100, 0, 100)
        assert icr == 1.0
        assert flag is True

    def test_interest_zero_returns_none_with_debt_free_label(self):
        icr, label, flag = interest_coverage(200, 50, 0)
        assert icr is None
        assert label == "Debt Free"
        assert flag is False

    def test_none_interest_returns_none_with_debt_free_label(self):
        icr, label, flag = interest_coverage(200, 50, None)
        assert icr is None
        assert label == "Debt Free"
        assert flag is False

    def test_none_operating_profit_treated_as_zero(self):
        icr, label, flag = interest_coverage(None, 50, 100)
        assert icr == 0.5
        assert flag is True


class TestNetDebt:
    """Net Debt = borrowings - investments"""

    def test_positive_net_debt(self):
        assert net_debt(1000, 200) == 800.0

    def test_negative_net_debt(self):
        assert net_debt(200, 1000) == -800.0

    def test_zero_borrowings(self):
        assert net_debt(0, 500) == -500.0

    def test_none_inputs_treated_as_zero(self):
        assert net_debt(None, 500) == -500.0
        assert net_debt(500, None) == 500.0
        assert net_debt(None, None) == 0.0


class TestAssetTurnover:
    """Asset Turnover = sales / total_assets"""

    def test_normal_case(self):
        assert asset_turnover(2000, 1000) == 2.0

    def test_zero_assets_returns_none(self):
        assert asset_turnover(1000, 0) is None

    def test_negative_assets_returns_none(self):
        assert asset_turnover(1000, -500) is None

    def test_none_inputs_return_none(self):
        assert asset_turnover(None, 1000) is None
        assert asset_turnover(1000, None) is None