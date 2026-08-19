"""tests/kpi/test_cagr.py — 10+ tests for CAGR engine and edge cases"""
import pandas as pd
import pytest
from src.analytics.cagr import (
    compute_cagr,
    compute_windowed_cagr,
    compute_revenue_cagr,
    compute_pat_cagr,
    compute_eps_cagr,
    DECLINE_TO_LOSS,
    TURNAROUND,
    BOTH_NEGATIVE,
    ZERO_BASE,
    INSUFFICIENT,
    NORMAL,
)


class TestComputeCAGR:
    """Core CAGR formula: ((end/start)^(1/n) - 1) * 100"""

    def test_normal_positive_growth(self):
        # 100 -> 200 over 5 years -> 14.87%
        cagr, flag = compute_cagr(100, 200, 5)
        assert cagr == 14.87
        assert flag == NORMAL

    def test_normal_zero_growth(self):
        # 100 -> 100 over 5 years -> 0%
        cagr, flag = compute_cagr(100, 100, 5)
        assert cagr == 0.0
        assert flag == NORMAL

    def test_decline_to_loss(self):
        # +100 -> -50 -> DECLINE_TO_LOSS
        cagr, flag = compute_cagr(100, -50, 5)
        assert cagr is None
        assert flag == DECLINE_TO_LOSS

    def test_turnaround(self):
        # -100 -> +200 -> TURNAROUND
        cagr, flag = compute_cagr(-100, 200, 5)
        assert cagr is None
        assert flag == TURNAROUND

    def test_both_negative(self):
        # -100 -> -50 -> BOTH_NEGATIVE
        cagr, flag = compute_cagr(-100, -50, 5)
        assert cagr is None
        assert flag == BOTH_NEGATIVE

    def test_zero_base(self):
        # 0 -> 100 -> ZERO_BASE
        cagr, flag = compute_cagr(0, 100, 5)
        assert cagr is None
        assert flag == ZERO_BASE

    def test_negative_base(self):
        # -50 -> 100 -> TURNAROUND (base is negative)
        cagr, flag = compute_cagr(-50, 100, 5)
        assert cagr is None
        assert flag == TURNAROUND

    def test_none_start(self):
        cagr, flag = compute_cagr(None, 100, 5)
        assert cagr is None
        assert flag == INSUFFICIENT

    def test_none_end(self):
        cagr, flag = compute_cagr(100, None, 5)
        assert cagr is None
        assert flag == INSUFFICIENT

    def test_zero_n_years(self):
        cagr, flag = compute_cagr(100, 200, 0)
        assert cagr is None
        assert flag == INSUFFICIENT

    def test_negative_n_years(self):
        cagr, flag = compute_cagr(100, 200, -1)
        assert cagr is None
        assert flag == INSUFFICIENT


class TestWindowedCAGR:
    """Windowed CAGR with time-series data"""

    def test_5yr_cagr_normal(self):
        # 6 years of data (2024 to 2019), compute 5yr CAGR
        series = pd.Series(
            [100, 110, 121, 133, 146, 161],  # 2024-03 down to 2019-03
            index=['2024-03', '2023-03', '2022-03', '2021-03', '2020-03', '2019-03']
        )
        cagr, flag = compute_windowed_cagr(series, window_years=5)
        # Start=161 (2019), End=100 (2024) -> negative growth
        assert flag == NORMAL
        assert cagr < 0  # declining

    def test_5yr_cagr_positive(self):
        # Sales doubled in 5 years
        series = pd.Series(
            [200, 180, 162, 146, 131, 118],  # most recent first
            index=['2024-03', '2023-03', '2022-03', '2021-03', '2020-03', '2019-03']
        )
        cagr, flag = compute_windowed_cagr(series, window_years=5)
        # Start=118 (2019), End=200 (2024) -> positive growth
        assert flag == NORMAL
        assert cagr > 0

    def test_insufficient_data(self):
        # Only 2 years, but window needs 3+
        series = pd.Series(
            [100, 200],
            index=['2024-03', '2023-03']
        )
        cagr, flag = compute_windowed_cagr(series, window_years=3)
        assert cagr is None
        assert flag == INSUFFICIENT

    def test_empty_series(self):
        series = pd.Series([], dtype=float)
        cagr, flag = compute_windowed_cagr(series, window_years=5)
        assert cagr is None
        assert flag == INSUFFICIENT

    def test_none_series(self):
        cagr, flag = compute_windowed_cagr(None, window_years=5)
        assert cagr is None
        assert flag == INSUFFICIENT


class TestMetricCAGRFunctions:
    """Convenience wrappers for revenue/PAT/EPS CAGR"""

    def test_revenue_cagr_5yr(self):
        years = ['2024-03', '2023-03', '2022-03', '2021-03', '2020-03', '2019-03']
        sales = [200, 180, 162, 146, 131, 118]
        cagr, flag = compute_revenue_cagr(years, sales, window_years=5)
        assert flag == NORMAL
        assert cagr > 0

    def test_pat_cagr_5yr(self):
        years = ['2024-03', '2023-03', '2022-03', '2021-03', '2020-03', '2019-03']
        pat = [50, 40, 32, 25, 20, 16]
        cagr, flag = compute_pat_cagr(years, pat, window_years=5)
        assert flag == NORMAL
        assert cagr > 0

    def test_eps_cagr_5yr(self):
        years = ['2024-03', '2023-03', '2022-03', '2021-03', '2020-03', '2019-03']
        eps = [25, 20, 16, 13, 10, 8]
        cagr, flag = compute_eps_cagr(years, eps, window_years=5)
        assert flag == NORMAL
        assert cagr > 0

    def test_revenue_cagr_turnaround(self):
        # Revenue was negative, now positive
        years = ['2024-03', '2023-03', '2022-03', '2021-03', '2020-03', '2019-03']
        sales = [100, -50, -80, -100, -120, -150]
        cagr, flag = compute_revenue_cagr(years, sales, window_years=5)
        assert flag == TURNAROUND
        assert cagr is None