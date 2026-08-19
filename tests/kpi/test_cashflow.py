"""tests/kpi/test_cashflow.py — 10+ tests for cash flow KPIs and capital allocation"""
import pandas as pd
import pytest
from src.analytics.cashflow_kpis import (
    free_cash_flow,
    cfo_quality_score,
    capex_intensity,
    fcf_conversion_rate,
    classify_capital_allocation,
    get_sign_symbol,
    PATTERN_REINVESTOR,
    PATTERN_SHAREHOLDER_RETURNS,
    PATTERN_LIQUIDATING,
    PATTERN_DISTRESS,
    PATTERN_GROWTH_DEBT,
    PATTERN_CASH_ACCUMULATOR,
    PATTERN_PRE_REVENUE,
    PATTERN_MIXED,
)


class TestFreeCashFlow:
    """FCF = CFO + CFI"""

    def test_positive_fcf(self):
        # CFO=500, CFI=-200 (capex) -> FCF=300
        assert free_cash_flow(500, -200) == 300.0

    def test_negative_fcf(self):
        # CFO=500, CFI=-800 (heavy capex) -> FCF=-300
        assert free_cash_flow(500, -800) == -300.0

    def test_zero_fcf(self):
        assert free_cash_flow(0, 0) == 0.0

    def test_none_inputs_treated_as_zero(self):
        assert free_cash_flow(None, None) == 0.0
        assert free_cash_flow(500, None) == 500.0
        assert free_cash_flow(None, -200) == -200.0


class TestCFOQualityScore:
    """CFO Quality = avg(CFO/PAT) over 5 years"""

    def test_high_quality(self):
        cfo = pd.Series([110, 105, 120], index=['2024', '2023', '2022'])
        pat = pd.Series([100, 100, 100], index=['2024', '2023', '2022'])
        ratio, label = cfo_quality_score(cfo, pat)
        # avg = (1.1 + 1.05 + 1.2) / 3 = 1.12
        assert ratio == 1.12
        assert label == "High Quality"

    def test_moderate_quality(self):
        cfo = pd.Series([70, 80, 60], index=['2024', '2023', '2022'])
        pat = pd.Series([100, 100, 100], index=['2024', '2023', '2022'])
        ratio, label = cfo_quality_score(cfo, pat)
        # avg = 0.7
        assert ratio == 0.7
        assert label == "Moderate"

    def test_accrual_risk(self):
        cfo = pd.Series([30, 20, 40], index=['2024', '2023', '2022'])
        pat = pd.Series([100, 100, 100], index=['2024', '2023', '2022'])
        ratio, label = cfo_quality_score(cfo, pat)
        # avg = 0.3
        assert ratio == 0.3
        assert label == "Accrual Risk"

    def test_pat_zero_returns_none(self):
        cfo = pd.Series([100, 100], index=['2024', '2023'])
        pat = pd.Series([0, 0], index=['2024', '2023'])
        ratio, label = cfo_quality_score(cfo, pat)
        assert ratio is None
        assert label is None

    def test_none_series_returns_none(self):
        ratio, label = cfo_quality_score(None, None)
        assert ratio is None
        assert label is None


class TestCapExIntensity:
    """CapEx Intensity = abs(CFI) / sales * 100"""

    def test_asset_light(self):
        # abs(CFI) = 100, sales = 10000 -> 1% (Asset Light)
        assert capex_intensity(-100, 10000) == 1.0

    def test_moderate(self):
        # abs(CFI) = 500, sales = 10000 -> 5% (Moderate)
        assert capex_intensity(-500, 10000) == 5.0

    def test_capital_intensive(self):
        # abs(CFI) = 1500, sales = 10000 -> 15% (Capital Intensive)
        assert capex_intensity(-1500, 10000) == 15.0

    def test_zero_sales_returns_none(self):
        assert capex_intensity(-100, 0) is None

    def test_none_inputs_return_none(self):
        assert capex_intensity(None, 1000) is None
        assert capex_intensity(-100, None) is None


class TestFCFConversionRate:
    """FCF Conversion = FCF / operating_profit * 100"""

    def test_normal_case(self):
        assert fcf_conversion_rate(200, 500) == 40.0

    def test_above_100_percent(self):
        # FCF > operating_profit (e.g. D&A adds back)
        assert fcf_conversion_rate(600, 500) == 120.0

    def test_zero_operating_profit_returns_none(self):
        assert fcf_conversion_rate(200, 0) is None

    def test_none_inputs_return_none(self):
        assert fcf_conversion_rate(None, 500) is None
        assert fcf_conversion_rate(200, None) is None


class TestCapitalAllocation:
    """8-pattern classifier based on sign(CFO, CFI, CFF)"""

    def test_reinvestor(self):
        # (+,-,-) = Reinvestor
        assert classify_capital_allocation(500, -200, -100) == PATTERN_REINVESTOR

    def test_shareholder_returns(self):
        # (+,-,-) with high CFO/PAT > 1.0
        assert classify_capital_allocation(500, -200, -100, cfo_pat_ratio=1.5) == PATTERN_SHAREHOLDER_RETURNS

    def test_liquidating_assets(self):
        # (+,+,-) = Liquidating Assets
        assert classify_capital_allocation(500, 200, -100) == PATTERN_LIQUIDATING

    def test_distress_signal(self):
        # (-,+,+) = Distress Signal
        assert classify_capital_allocation(-100, 200, 500) == PATTERN_DISTRESS

    def test_growth_funded_by_debt(self):
        # (-,-,+) = Growth Funded by Debt
        assert classify_capital_allocation(-100, -200, 500) == PATTERN_GROWTH_DEBT

    def test_cash_accumulator(self):
        # (+,+,+) = Cash Accumulator
        assert classify_capital_allocation(500, 200, 100) == PATTERN_CASH_ACCUMULATOR

    def test_pre_revenue(self):
        # (-,-,-) = Pre-Revenue
        assert classify_capital_allocation(-100, -200, -50) == PATTERN_PRE_REVENUE

    def test_mixed(self):
        # (+,-,+) = Mixed
        assert classify_capital_allocation(500, -200, 100) == PATTERN_MIXED

    def test_none_inputs_treated_as_zero(self):
        # All None -> Mixed (no pattern)
        assert classify_capital_allocation(None, None, None) == PATTERN_MIXED

    def test_zero_values_classified_as_mixed(self):
        # All 0 -> Mixed
        assert classify_capital_allocation(0, 0, 0) == PATTERN_MIXED


class TestGetSignSymbol:
    """Helper to get sign symbol"""

    def test_positive(self):
        assert get_sign_symbol(100) == "+"

    def test_negative(self):
        assert get_sign_symbol(-100) == "-"

    def test_zero(self):
        assert get_sign_symbol(0) == "0"

    def test_none_treated_as_zero(self):
        assert get_sign_symbol(None) == "0"