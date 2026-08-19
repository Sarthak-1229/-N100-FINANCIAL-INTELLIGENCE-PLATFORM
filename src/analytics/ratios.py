"""
src/analytics/ratios.py

Profitability, Leverage, and Efficiency ratio functions.
Each function = one formula. Pure, side-effect-free (except edge case logging).
All monetary values in Crore (Cr) unless stated otherwise.
"""

import os
from src.etl.normaliser import normalize_numeric


EDGE_CASE_LOG = os.path.join(os.path.dirname(__file__), "..", "..", "output", "ratio_edge_cases.log")


def _log_edge_case(company_id: str, year: str, formula: str, reason: str):
    """Append an edge case hit to the log file."""
    os.makedirs(os.path.dirname(EDGE_CASE_LOG), exist_ok=True)
    with open(EDGE_CASE_LOG, "a", encoding="utf-8") as f:
        f.write(f"{company_id},{year},{formula},{reason}\n")


def net_profit_margin(net_profit, sales, company_id=None, year=None) -> float | None:
    """
    NPM = net_profit / sales * 100

    Args:
        net_profit: Net profit (Cr)
        sales: Sales/Revenue (Cr)
        company_id: For edge case logging
        year: For edge case logging

    Returns:
        NPM percentage, or None if sales is None/0 or inputs are None
    """
    net_profit = normalize_numeric(net_profit)
    sales = normalize_numeric(sales)

    if net_profit is None or sales is None or sales <= 0:
        if company_id and year:
            _log_edge_case(company_id, year, "NPM", f"sales is None or <= 0: {sales}")
        return None

    return round((net_profit / sales) * 100, 2)


def operating_profit_margin(operating_profit, sales, opm_percentage=None, company_id=None, year=None):
    """
    OPM = operating_profit / sales * 100
    Cross-check against source opm_percentage field (±1% tolerance).

    Args:
        operating_profit: Operating profit (Cr)
        sales: Sales/Revenue (Cr)
        opm_percentage: Source OPM percentage for cross-check (optional)
        company_id: For edge case logging
        year: For edge case logging

    Returns:
        Tuple of (computed OPM %, mismatch_flag)
        mismatch_flag = True if opm_percentage provided and difference > 1%
    """
    operating_profit = normalize_numeric(operating_profit)
    sales = normalize_numeric(sales)

    if operating_profit is None or sales is None or sales <= 0:
        if company_id and year:
            _log_edge_case(company_id, year, "OPM", f"operating_profit or sales is None/<=0: sales={sales}")
        return None, False

    computed_opm = round((operating_profit / sales) * 100, 2)
    mismatch = False

    if opm_percentage is not None:
        opm_percentage = normalize_numeric(opm_percentage)
        if opm_percentage is not None and abs(computed_opm - opm_percentage) > 1.0:
            mismatch = True
            if company_id and year:
                _log_edge_case(company_id, year, "OPM", f"mismatch > 1%: computed={computed_opm}, source={opm_percentage}")

    return computed_opm, mismatch


def return_on_equity(net_profit, equity_capital, reserves, company_id=None, year=None) -> float | None:
    """
    ROE = net_profit / (equity_capital + reserves) * 100

    Args:
        net_profit: Net profit (Cr)
        equity_capital: Equity share capital (Cr)
        reserves: Reserves and surplus (Cr)
        company_id: For edge case logging
        year: For edge case logging

    Returns:
        ROE percentage, or None if equity+reserves <= 0 or inputs are None
    """
    net_profit = normalize_numeric(net_profit)
    equity_capital = normalize_numeric(equity_capital)
    reserves = normalize_numeric(reserves)

    if net_profit is None or equity_capital is None or reserves is None:
        if company_id and year:
            _log_edge_case(company_id, year, "ROE", "input is None")
        return None

    equity_base = equity_capital + reserves
    if equity_base <= 0:
        if company_id and year:
            _log_edge_case(company_id, year, "ROE", f"equity+reserves <= 0: {equity_base}")
        return None

    return round((net_profit / equity_base) * 100, 2)


def return_on_capital_employed(operating_profit, depreciation, equity_capital, reserves, borrowings,
                                total_assets, is_financial=False, company_id=None, year=None) -> float | None:
    """
    ROCE = EBIT / (equity + reserves + borrowings) * 100
    EBIT = operating_profit - depreciation

    For Financials (banks/NBFCs/insurance): use net_profit / total_assets * 100 instead
    (ROA proxy since bank ROCE is not meaningful)

    Args:
        operating_profit: Operating profit (Cr)
        depreciation: Depreciation (Cr)
        equity_capital: Equity share capital (Cr)
        reserves: Reserves and surplus (Cr)
        borrowings: Total borrowings (Cr)
        total_assets: Total assets (Cr) - used for financials
        is_financial: True if company is in Financials broad_sector
        company_id: For edge case logging
        year: For edge case logging

    Returns:
        ROCE percentage, or None if denominator <= 0 or inputs are None
    """
    operating_profit = normalize_numeric(operating_profit)
    depreciation = normalize_numeric(depreciation)
    equity_capital = normalize_numeric(equity_capital)
    reserves = normalize_numeric(reserves)
    borrowings = normalize_numeric(borrowings)
    total_assets = normalize_numeric(total_assets)

    # Check for None inputs
    if (operating_profit is None or depreciation is None or
        equity_capital is None or reserves is None or borrowings is None):
        if company_id and year:
            _log_edge_case(company_id, year, "ROCE", "input is None")
        return None

    if is_financial:
        # Banks/NBFCs: use ROA proxy
        if total_assets is None or total_assets <= 0:
            if company_id and year:
                _log_edge_case(company_id, year, "ROCE", "financial: total_assets <= 0")
            return None
        net_profit = normalize_numeric(operating_profit)  # approximate EBIT as net proxy for banks
        # Actually for banks we need net_profit; operating_profit is not the right metric
        # This function will be called with net_profit passed as operating_profit for financials
        return round((net_profit / total_assets) * 100, 2)

    ebit = operating_profit - (depreciation if depreciation is not None else 0)
    capital_employed = equity_capital + reserves + (borrowings if borrowings is not None else 0)

    if capital_employed <= 0:
        if company_id and year:
            _log_edge_case(company_id, year, "ROCE", f"capital_employed <= 0: {capital_employed}")
        return None

    return round((ebit / capital_employed) * 100, 2)


def return_on_assets(net_profit, total_assets, company_id=None, year=None) -> float | None:
    """
    ROA = net_profit / total_assets * 100

    Args:
        net_profit: Net profit (Cr)
        total_assets: Total assets (Cr)
        company_id: For edge case logging
        year: For edge case logging

    Returns:
        ROA percentage, or None if total_assets <= 0 or inputs are None
    """
    net_profit = normalize_numeric(net_profit)
    total_assets = normalize_numeric(total_assets)

    if net_profit is None or total_assets is None or total_assets <= 0:
        if company_id and year:
            _log_edge_case(company_id, year, "ROA", "total_assets <= 0 or None")
        return None

    return round((net_profit / total_assets) * 100, 2)


def debt_to_equity(borrowings, equity_capital, reserves, is_financial=False, company_id=None, year=None):
    """
    D/E = borrowings / (equity_capital + reserves)
    Returns 0 (not None) if borrowings = 0 (debt-free).
    High leverage flag: D/E > 5 AND not financial sector.

    Args:
        borrowings: Total borrowings (Cr)
        equity_capital: Equity share capital (Cr)
        reserves: Reserves and surplus (Cr)
        is_financial: True if company is in Financials broad_sector
        company_id: For edge case logging
        year: For edge case logging

    Returns:
        Tuple of (D/E ratio, high_leverage_flag)
    """
    borrowings = normalize_numeric(borrowings)
    equity_capital = normalize_numeric(equity_capital)
    reserves = normalize_numeric(reserves)

    if borrowings is None:
        borrowings = 0
    if equity_capital is None:
        equity_capital = 0
    if reserves is None:
        reserves = 0

    equity_base = equity_capital + reserves

    if borrowings == 0:
        return 0.0, False  # Debt-free company

    if equity_base <= 0:
        if company_id and year:
            _log_edge_case(company_id, year, "DE", f"equity+reserves <= 0: {equity_base}")
        return None, False

    de_ratio = round(borrowings / equity_base, 2)
    high_leverage = (de_ratio > 5.0) and (not is_financial)

    return de_ratio, high_leverage


def interest_coverage(operating_profit, other_income, interest, company_id=None, year=None):
    """
    ICR = (operating_profit + other_income) / interest
    Returns None if interest = 0 (debt-free), with label "Debt Free".
    Low ICR warning flag: ICR < 1.5

    Args:
        operating_profit: Operating profit (Cr)
        other_income: Other income (Cr)
        interest: Interest expense (Cr)
        company_id: For edge case logging
        year: For edge case logging

    Returns:
        Tuple of (ICR value, label, low_icr_flag)
        label = "Debt Free" if interest=0, else None
        low_icr_flag = True if ICR < 1.5
    """
    operating_profit = normalize_numeric(operating_profit)
    other_income = normalize_numeric(other_income)
    interest = normalize_numeric(interest)

    if operating_profit is None:
        operating_profit = 0
    if other_income is None:
        other_income = 0

    if interest is None or interest == 0:
        if company_id and year:
            _log_edge_case(company_id, year, "ICR", "interest = 0 (Debt Free)")
        return None, "Debt Free", False

    ebit = operating_profit + other_income
    icr = round(ebit / interest, 2)
    low_icr = icr < 1.5

    return icr, None, low_icr


def net_debt(borrowings, investments) -> float:
    """
    Net Debt = borrowings - investments (investments as liquid asset proxy)

    Args:
        borrowings: Total borrowings (Cr)
        investments: Investments (Cr)

    Returns:
        Net debt (Cr) - can be negative if investments > borrowings
    """
    borrowings = normalize_numeric(borrowings) or 0
    investments = normalize_numeric(investments) or 0

    return round(borrowings - investments, 2)


def asset_turnover(sales, total_assets, company_id=None, year=None) -> float | None:
    """
    Asset Turnover = sales / total_assets

    Args:
        sales: Sales/Revenue (Cr)
        total_assets: Total assets (Cr)
        company_id: For edge case logging
        year: For edge case logging

    Returns:
        Asset turnover ratio, or None if total_assets <= 0 or inputs are None
    """
    sales = normalize_numeric(sales)
    total_assets = normalize_numeric(total_assets)

    if sales is None or total_assets is None or total_assets <= 0:
        if company_id and year:
            _log_edge_case(company_id, year, "AT", "total_assets <= 0 or None")
        return None

    return round(sales / total_assets, 2)