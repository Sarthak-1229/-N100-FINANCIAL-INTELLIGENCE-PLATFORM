"""
tests/kpi/test_ratios_extended.py — Extended unit tests for ratio calculations
Covers: ROE with positive equity, ROE with negative equity (returns None), D/E for debt-free company (returns 0),
ICR when interest=0 (returns None), D/E > 5 flag for non-financial company, CAGR turnaround flag,
CAGR decline-to-loss, normal CAGR calculation, OPM cross-check divergence flag, CFO quality score calculation
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.analytics.ratios import (
    return_on_equity,
    debt_to_equity,
    interest_coverage,
    net_profit_margin,
    operating_profit_margin
)
from src.analytics.cagr import compute_cagr
from src.analytics.cashflow_kpis import cfo_quality_score, free_cash_flow
import pandas as pd


class TestROE:
    """Test Return on Equity calculations"""

    def test_roe_positive_equity(self):
        """Test ROE with positive equity returns correct value"""
        # net_profit = 100, equity_capital = 50, reserves = 50
        # ROE = 100 / (50 + 50) * 100 = 100%
        result = return_on_equity(100, 50, 50)
        assert result == 100.0

    def test_roe_negative_equity_returns_none(self):
        """Test ROE with negative equity returns None"""
        # net_profit = 100, equity_capital = -50, reserves = 0
        # Total equity = -50 < 0, should return None
        result = return_on_equity(100, -50, 0)
        assert result is None

    def test_roe_zero_equity_returns_none(self):
        """Test ROE with zero equity returns None"""
        result = return_on_equity(100, 0, 0)
        assert result is None

    def test_roe_none_inputs_return_none(self):
        """Test ROE with None inputs returns None"""
        assert return_on_equity(None, 50, 50) is None
        assert return_on_equity(100, None, 50) is None
        assert return_on_equity(100, 50, None) is None

    def test_roe_reserves_only(self):
        """Test ROE with only reserves (no equity capital)"""
        # net_profit = 100, equity_capital = 0, reserves = 100
        # ROE = 100 / 100 * 100 = 100%
        result = return_on_equity(100, 0, 100)
        assert result == 100.0


class TestDebtToEquity:
    """Test Debt to Equity calculations"""

    def test_de_debt_free_returns_zero(self):
        """Test D/E for debt-free company (borrowings=0) returns 0"""
        # borrowings = 0, equity_capital = 100, reserves = 100
        # D/E = 0 / 200 = 0
        result, flag = debt_to_equity(0, 100, 100)
        assert result == 0.0
        assert flag is False

    def test_de_high_leverage_flag_non_financial(self):
        """Test D/E > 5 flag for non-financial company"""
        # This test verifies the logic - the flag would be set in the calling code
        # For D/E calculation itself:
        result, flag = debt_to_equity(1000, 100, 50)  # D/E = 1000/150 = 6.67
        assert result == 6.67  # D/E > 5
        assert flag is True  # Should flag as high leverage for non-financial

    def test_de_high_leverage_no_flag_for_financial(self):
        """Test D/E > 5 no flag for financial company"""
        # Financial companies can have high D/E
        result, flag = debt_to_equity(1000, 100, 50, is_financial=True)
        assert result == 6.67  # Just verify calculation is correct
        assert flag is False  # No flag for financial

    def test_de_negative_equity_returns_none(self):
        """Test D/E with negative equity returns None"""
        result, flag = debt_to_equity(100, -50, 0)
        assert result is None

    def test_de_none_borrowings_treated_as_zero(self):
        """Test D/E with None borrowings treated as 0"""
        result, flag = debt_to_equity(None, 100, 100)
        assert result == 0.0

    def test_de_normal_case(self):
        """Test normal D/E calculation"""
        result, flag = debt_to_equity(500, 1000, 500)  # 500/1500 = 0.33
        assert result == 0.33
        assert flag is False


class TestInterestCoverage:
    """Test Interest Coverage Ratio calculations"""

    def test_icr_interest_zero_returns_none(self):
        """Test ICR when interest=0 returns None (Debt Free)"""
        # operating_profit = 1000, other_income = 0, interest = 0
        result, label, flag = interest_coverage(1000, 0, 0)
        assert result is None  # Debt free
        assert label == "Debt Free"

    def test_icr_none_interest_returns_none(self):
        """Test ICR with None interest returns None"""
        result, label, flag = interest_coverage(1000, 0, None)
        assert result is None
        assert label == "Debt Free"

    def test_icr_none_operating_profit_treated_as_zero(self):
        """Test ICR with None operating_profit treated as 0"""
        result, label, flag = interest_coverage(None, 0, 100)
        assert result == 0.0
        assert flag is True  # Low ICR flag should be True

    def test_icr_normal_case(self):
        """Test normal ICR calculation"""
        # (operating_profit + other_income) / interest
        # (1000 + 200) / 100 = 12
        result, label, flag = interest_coverage(1000, 200, 100)
        assert result == 12.0
        assert label is None
        assert flag is False


class TestCAGR:
    """Test CAGR calculations including edge cases"""

    def test_cagr_turnaround_flag(self):
        """Test CAGR turnaround flag (base < 0, end > 0)"""
        # base = -100, end = 100, n_years = 5
        cagr, flag = compute_cagr(-100, 100, 5)
        assert cagr is None  # Should return None as per spec
        assert flag == "TURNAROUND"

    def test_cagr_decline_to_loss(self):
        """Test CAGR decline to loss (base > 0, end < 0)"""
        cagr, flag = compute_cagr(100, -50, 5)
        assert cagr is None  # Should return None as per spec
        assert flag == "DECLINE_TO_LOSS"

    def test_cagr_normal_positive_growth(self):
        """Test normal CAGR calculation with positive growth"""
        # (200/100)^(1/5) - 1 = 2^0.2 - 1 = 0.1487 = 14.87%
        cagr, flag = compute_cagr(100, 200, 5)
        assert cagr == 14.87  # Rounded
        assert flag == "NORMAL"

    def test_cagr_normal_zero_growth(self):
        """Test CAGR with zero growth"""
        cagr, flag = compute_cagr(100, 100, 5)
        assert cagr == 0.0
        assert flag == "NORMAL"

    def test_cagr_both_negative(self):
        """Test CAGR with both base and end negative"""
        cagr, flag = compute_cagr(-200, -100, 5)
        assert cagr is None  # Should return None as per spec
        assert flag == "BOTH_NEGATIVE"

    def test_cagr_zero_base(self):
        """Test CAGR with zero base returns None"""
        cagr, flag = compute_cagr(0, 100, 5)
        assert cagr is None
        assert flag == "ZERO_BASE"

    def test_cagr_negative_base(self):
        """Test CAGR with negative base but positive end (turnaround)"""
        cagr, flag = compute_cagr(-100, 50, 5)
        assert cagr is None  # Should return None as per spec
        assert flag == "TURNAROUND"


class TestOPMCrossCheck:
    """Test Operating Profit Margin cross-check divergence flag"""

    def test_opm_cross_check_mismatch_flag(self):
        """Test OPM cross-check mismatch flag when divergence > 1%"""
        # operating_profit = 100, sales = 1000, opm_percentage = 15
        # Calculated OPM = 10%, provided = 15%, divergence = 5% > 1%
        # The function should flag this
        from src.analytics.ratios import operating_profit_margin
        opm, mismatch = operating_profit_margin(100, 1000, 15.0)
        # The result should still be the calculated value (10%)
        # but the edge case should be logged
        assert opm == 10.0
        assert mismatch is True

    def test_opm_cross_check_within_tolerance(self):
        """Test OPM cross-check within tolerance (<= 1%)"""
        # operating_profit = 100, sales = 1000, opm_percentage = 10.5
        # Calculated = 10%, provided = 10.5%, divergence = 0.5% <= 1%
        from src.analytics.ratios import operating_profit_margin
        opm, mismatch = operating_profit_margin(100, 1000, 10.5)
        assert opm == 10.0
        assert mismatch is False

    def test_opm_zero_sales_returns_none(self):
        """Test OPM with zero sales returns None"""
        from src.analytics.ratios import operating_profit_margin
        opm, mismatch = operating_profit_margin(100, 0, 10.0)
        assert opm is None
        assert mismatch is False

    def test_opm_none_operating_profit_returns_none(self):
        """Test OPM with None operating_profit returns None"""
        from src.analytics.ratios import operating_profit_margin
        opm, mismatch = operating_profit_margin(None, 1000, 10.0)
        assert opm is None
        assert mismatch is False

    def test_opm_none_opm_percentage_no_crash(self):
        """Test OPM with None opm_percentage doesn't crash"""
        from src.analytics.ratios import operating_profit_margin
        opm, mismatch = operating_profit_margin(100, 1000, None)
        assert opm == 10.0
        assert mismatch is False


class TestCFOQualityScore:
    """Test CFO Quality Score calculation"""

    def test_cfo_quality_score_high_quality(self):
        """Test CFO Quality Score - High Quality (> 1.0)"""
        cfo = pd.Series([110, 105, 120], index=['2024', '2023', '2022'])
        pat = pd.Series([100, 100, 100], index=['2024', '2023', '2022'])
        ratio, label = cfo_quality_score(cfo, pat)
        # avg = (1.1 + 1.05 + 1.2) / 3 = 1.1166...
        assert ratio == 1.12
        assert label == "High Quality"

    def test_cfo_quality_score_moderate(self):
        """Test CFO Quality Score - Moderate (0.5 - 1.0)"""
        cfo = pd.Series([70, 80, 60], index=['2024', '2023', '2022'])
        pat = pd.Series([100, 100, 100], index=['2024', '2023', '2022'])
        ratio, label = cfo_quality_score(cfo, pat)
        assert ratio == 0.7
        assert label == "Moderate"

    def test_cfo_quality_score_accrual_risk(self):
        """Test CFO Quality Score - Accrual Risk (< 0.5)"""
        cfo = pd.Series([30, 20, 40], index=['2024', '2023', '2022'])
        pat = pd.Series([100, 100, 100], index=['2024', '2023', '2022'])
        ratio, label = cfo_quality_score(cfo, pat)
        assert ratio == 0.3
        assert label == "Accrual Risk"

    def test_cfo_quality_score_pat_zero_returns_none(self):
        """Test CFO Quality Score with PAT = 0 returns None"""
        cfo = pd.Series([100, 100], index=['2024', '2023'])
        pat = pd.Series([0, 0], index=['2024', '2023'])
        ratio, label = cfo_quality_score(cfo, pat)
        assert ratio is None
        assert label is None

    def test_cfo_quality_score_none_series_returns_none(self):
        """Test CFO Quality Score with None series returns None"""
        ratio, label = cfo_quality_score(None, None)
        assert ratio is None
        assert label is None


class TestNetProfitMargin:
    """Test Net Profit Margin calculations"""

    def test_npm_normal_case(self):
        """Test normal NPM calculation"""
        # net_profit = 100, sales = 1000 -> NPM = 10%
        result = net_profit_margin(100, 1000)
        assert result == 10.0

    def test_npm_zero_sales_returns_none(self):
        """Test NPM with zero sales returns None"""
        result = net_profit_margin(100, 0)
        assert result is None

    def test_npm_negative_sales_returns_none(self):
        """Test NPM with negative sales returns None"""
        result = net_profit_margin(100, -1000)
        assert result is None


class TestFreeCashFlow:
    """Test Free Cash Flow calculations"""

    def test_fcf_positive(self):
        """Test positive FCF"""
        # CFO = 500, CFI = -200 (capex) -> FCF = 300
        result = free_cash_flow(500, -200)
        assert result == 300.0

    def test_fcf_negative(self):
        """Test negative FCF"""
        result = free_cash_flow(500, -800)
        assert result == -300.0

    def test_fcf_none_inputs_treated_as_zero(self):
        """Test FCF with None inputs treated as zero"""
        assert free_cash_flow(None, None) == 0.0
        assert free_cash_flow(500, None) == 500.0
        assert free_cash_flow(None, -200) == -200.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])