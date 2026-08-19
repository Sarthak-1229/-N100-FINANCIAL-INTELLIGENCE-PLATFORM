"""
src/analytics/cashflow_kpis.py

Cash flow KPIs and capital allocation classifier.
All monetary values in Crore (Cr) unless stated otherwise.
"""
import pandas as pd
from src.etl.normaliser import normalize_numeric


# Capital allocation 8-pattern labels
PATTERN_REINVESTOR = "Reinvestor"  # (+,-,-)
PATTERN_SHAREHOLDER_RETURNS = "Shareholder Returns"  # (+,-,-) with high CFO/PAT
PATTERN_LIQUIDATING = "Liquidating Assets"  # (+,+,-)
PATTERN_DISTRESS = "Distress Signal"  # (-,+,+)
PATTERN_GROWTH_DEBT = "Growth Funded by Debt"  # (-,-,+)
PATTERN_CASH_ACCUMULATOR = "Cash Accumulator"  # (+,+,+)
PATTERN_PRE_REVENUE = "Pre-Revenue"  # (-,-,-)
PATTERN_MIXED = "Mixed"  # (+,-,+)


def free_cash_flow(operating_activity, investing_activity) -> float:
    """
    FCF = operating_activity + investing_activity
    Negative value is allowed (and common for growth companies).

    Args:
        operating_activity: Cash from operating activities (Cr)
        investing_activity: Cash from investing activities (Cr, usually negative)

    Returns:
        Free cash flow (Cr), or 0 if both inputs are None
    """
    operating_activity = normalize_numeric(operating_activity) or 0
    investing_activity = normalize_numeric(investing_activity) or 0

    return round(operating_activity + investing_activity, 2)


def cfo_quality_score(cfo_series: pd.Series, pat_series: pd.Series):
    """
    CFO Quality = avg(CFO / PAT) over 5 years
    > 1.0 = High Quality
    0.5-1.0 = Moderate
    < 0.5 = Accrual Risk
    Returns None if PAT = 0

    Args:
        cfo_series: Series of CFO values
        pat_series: Series of PAT (net profit) values (same length)

    Returns:
        Tuple of (avg_ratio, label)
    """
    if cfo_series is None or pat_series is None:
        return None, None

    if len(cfo_series) == 0 or len(pat_series) == 0:
        return None, None

    # Align series by index
    cfo_aligned = cfo_series.reindex(pat_series.index)

    # Compute ratios
    ratios = []
    for idx in pat_series.index:
        cfo = normalize_numeric(cfo_aligned.get(idx))
        pat = normalize_numeric(pat_series.get(idx))

        if pat is None or pat == 0:
            continue
        if cfo is None:
            continue

        ratios.append(cfo / pat)

    if not ratios:
        return None, None

    avg_ratio = sum(ratios) / len(ratios)
    avg_ratio = round(avg_ratio, 2)

    if avg_ratio > 1.0:
        label = "High Quality"
    elif avg_ratio >= 0.5:
        label = "Moderate"
    else:
        label = "Accrual Risk"

    return avg_ratio, label


def capex_intensity(investing_activity, sales) -> float | None:
    """
    CapEx Intensity = abs(investing_activity) / sales * 100
    < 3% = Asset Light
    3-8% = Moderate
    > 8% = Capital Intensive

    Args:
        investing_activity: Cash from investing activities (Cr, usually negative)
        sales: Sales/Revenue (Cr)

    Returns:
        CapEx intensity percentage, or None if sales is None/<=0
    """
    investing_activity = normalize_numeric(investing_activity)
    sales = normalize_numeric(sales)

    if investing_activity is None or sales is None or sales <= 0:
        return None

    return round((abs(investing_activity) / sales) * 100, 2)


def fcf_conversion_rate(fcf, operating_profit) -> float | None:
    """
    FCF Conversion Rate = FCF / operating_profit * 100

    Args:
        fcf: Free cash flow (Cr)
        operating_profit: Operating profit (Cr)

    Returns:
        FCF conversion percentage, or None if operating_profit is None/0
    """
    fcf = normalize_numeric(fcf)
    operating_profit = normalize_numeric(operating_profit)

    if fcf is None or operating_profit is None or operating_profit == 0:
        return None

    return round((fcf / operating_profit) * 100, 2)


def classify_capital_allocation(cfo, cfi, cff, cfo_pat_ratio=None):
    """
    8-pattern capital allocation classifier based on sign of (CFO, CFI, CFF).

    Patterns:
    (+,-,-) = Reinvestor (or Shareholder Returns if CFO/PAT > 1.0)
    (+,+,-) = Liquidating Assets
    (-,+,+) = Distress Signal
    (-,-,+) = Growth Funded by Debt
    (+,+,+) = Cash Accumulator
    (-,-,-) = Pre-Revenue
    (+,-,+) = Mixed

    Args:
        cfo: Operating cash flow
        cfi: Investing cash flow
        cff: Financing cash flow
        cfo_pat_ratio: Optional CFO/PAT ratio for distinguishing Reinvestor vs Shareholder Returns

    Returns:
        Pattern label string
    """
    cfo = normalize_numeric(cfo)
    cfi = normalize_numeric(cfi)
    cff = normalize_numeric(cff)

    # Treat None as 0 (no activity)
    if cfo is None:
        cfo = 0
    if cfi is None:
        cfi = 0
    if cff is None:
        cff = 0

    # Compute signs
    cfo_sign = "+" if cfo > 0 else ("-" if cfo < 0 else "0")
    cfi_sign = "+" if cfi > 0 else ("-" if cfi < 0 else "0")
    cff_sign = "+" if cff > 0 else ("-" if cff < 0 else "0")

    # All zero -> Mixed (no clear pattern)
    if cfo_sign == "0" and cfi_sign == "0" and cff_sign == "0":
        return PATTERN_MIXED

    # (+,-,-) = Reinvestor or Shareholder Returns
    if cfo_sign == "+" and cfi_sign == "-" and cff_sign == "-":
        if cfo_pat_ratio is not None and cfo_pat_ratio > 1.0:
            return PATTERN_SHAREHOLDER_RETURNS
        return PATTERN_REINVESTOR

    # (+,+,-) = Liquidating Assets
    if cfo_sign == "+" and cfi_sign == "+" and cff_sign == "-":
        return PATTERN_LIQUIDATING

    # (-,+,+) = Distress Signal
    if cfo_sign == "-" and cfi_sign == "+" and cff_sign == "+":
        return PATTERN_DISTRESS

    # (-,-,+) = Growth Funded by Debt
    if cfo_sign == "-" and cfi_sign == "-" and cff_sign == "+":
        return PATTERN_GROWTH_DEBT

    # (+,+,+) = Cash Accumulator
    if cfo_sign == "+" and cfi_sign == "+" and cff_sign == "+":
        return PATTERN_CASH_ACCUMULATOR

    # (-,-,-) = Pre-Revenue
    if cfo_sign == "-" and cfi_sign == "-" and cff_sign == "-":
        return PATTERN_PRE_REVENUE

    # (+,-,+) = Mixed
    if cfo_sign == "+" and cfi_sign == "-" and cff_sign == "+":
        return PATTERN_MIXED

    # Default: Mixed
    return PATTERN_MIXED


def get_sign_symbol(value) -> str:
    """Helper: return +, -, or 0 for a value."""
    if value is None:
        return "0"
    value = normalize_numeric(value)
    if value is None:
        return "0"
    if value > 0:
        return "+"
    elif value < 0:
        return "-"
    return "0"