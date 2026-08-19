"""
src/analytics/cagr.py

CAGR (Compound Annual Growth Rate) engine with all 6 edge cases.
CAGR = ((end / start) ^ (1/n) - 1) * 100

Edge cases:
- Positive + Positive: compute normally
- Positive + Negative: return None with flag DECLINE_TO_LOSS
- Negative + Positive: return None with flag TURNAROUND
- Negative + Negative: return None with flag BOTH_NEGATIVE
- Zero base: return None with flag ZERO_BASE
- Less than n years of data: return None with flag INSUFFICIENT
"""
import pandas as pd
from src.etl.normaliser import normalize_numeric


# Flag constants
DECLINE_TO_LOSS = "DECLINE_TO_LOSS"
TURNAROUND = "TURNAROUND"
BOTH_NEGATIVE = "BOTH_NEGATIVE"
ZERO_BASE = "ZERO_BASE"
INSUFFICIENT = "INSUFFICIENT"
NORMAL = "NORMAL"


def compute_cagr(start_value, end_value, n_years):
    """
    Core CAGR computation with all 6 edge case handlers.

    Args:
        start_value: Value at start of period (e.g. 2014-03)
        end_value: Value at end of period (e.g. 2024-03)
        n_years: Number of years between start and end

    Returns:
        Tuple of (cagr_value, flag)
        cagr_value: CAGR percentage, or None if edge case
        flag: One of NORMAL, DECLINE_TO_LOSS, TURNAROUND, BOTH_NEGATIVE, ZERO_BASE, INSUFFICIENT
    """
    start_value = normalize_numeric(start_value)
    end_value = normalize_numeric(end_value)

    # Edge case: missing inputs
    if start_value is None or end_value is None:
        return None, INSUFFICIENT

    # Edge case: n_years must be positive
    if n_years is None or n_years <= 0:
        return None, INSUFFICIENT

    # Edge case: zero base
    if start_value == 0:
        return None, ZERO_BASE

    # Edge case: both negative
    if start_value < 0 and end_value < 0:
        return None, BOTH_NEGATIVE

    # Edge case: decline to loss (positive -> negative)
    if start_value > 0 and end_value < 0:
        return None, DECLINE_TO_LOSS

    # Edge case: turnaround (negative -> positive)
    if start_value < 0 and end_value > 0:
        return None, TURNAROUND

    # Normal case: both positive (or both zero which is caught above)
    if start_value > 0 and end_value > 0:
        try:
            ratio = end_value / start_value
            cagr = (ratio ** (1.0 / n_years) - 1) * 100
            return round(cagr, 2), NORMAL
        except (ValueError, ZeroDivisionError, OverflowError):
            return None, INSUFFICIENT

    # start_value == 0 already handled above
    return None, INSUFFICIENT


def compute_windowed_cagr(series: pd.Series, window_years: int):
    """
    Compute CAGR over a FIXED window of years from a time series.
    Uses the most recent year as end, and finds the closest available
    year that is >= window_years before.

    Args:
        series: pandas Series with year ('YYYY-MM') as index, value as data
        window_years: Window size in years (3, 5, or 10)

    Returns:
        Tuple of (cagr_value, flag)
    """
    if series is None or series.empty:
        return None, INSUFFICIENT

    # Sort by year (ascending for chronological)
    sorted_series = series.sort_index(ascending=True)

    if len(sorted_series) < 2:
        return None, INSUFFICIENT

    # End is the most recent year
    end_year_str = sorted_series.index[-1]
    end_value = sorted_series.values[-1]

    # Parse end year
    try:
        end_y = int(str(end_year_str)[:4])
    except (ValueError, TypeError):
        return None, INSUFFICIENT

    # Target start year = end_year - window_years
    target_start_y = end_y - window_years

    # Find the closest available year >= target_start_y
    start_value = None
    start_y = None
    for idx, val in sorted_series.items():
        try:
            y = int(str(idx)[:4])
            if y >= target_start_y:
                start_value = val
                start_y = y
                break
        except (ValueError, TypeError):
            continue

    if start_value is None or start_y is None:
        return None, INSUFFICIENT

    actual_n = end_y - start_y
    if actual_n <= 0:
        return None, INSUFFICIENT

    # Require at least window_years - 1 actual gap (e.g., 4 for 5yr window)
    # This ensures we're computing over a meaningful window
    if actual_n < window_years - 1:
        return None, INSUFFICIENT

    return compute_cagr(start_value, end_value, actual_n)


def compute_revenue_cagr(years, sales_by_year, window_years):
    """Compute Revenue CAGR for a window."""
    series = pd.Series(sales_by_year, index=years)
    return compute_windowed_cagr(series, window_years)


def compute_pat_cagr(years, pat_by_year, window_years):
    """Compute PAT (net profit) CAGR for a window."""
    series = pd.Series(pat_by_year, index=years)
    return compute_windowed_cagr(series, window_years)


def compute_eps_cagr(years, eps_by_year, window_years):
    """Compute EPS CAGR for a window."""
    series = pd.Series(eps_by_year, index=years)
    return compute_windowed_cagr(series, window_years)