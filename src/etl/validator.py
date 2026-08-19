"""
src/etl/validator.py

Implements DQ-01 .. DQ-16 from the spec. Each check is a small pure
function that takes already-normalised data and returns True/False (or,
for row-level checks, is applied per-row by the loader). Keeping each
rule as its own tiny function is what makes 35+ unit tests realistic:
one or two tests per rule, each with a hand-picked input/expected pair.

Severity meanings:
    CRITICAL -> loader must reject the row (or halt, for DQ-01)
    WARNING  -> loader loads the row anyway, but logs it for review
    INFO     -> counter only, no action
"""
from dataclasses import dataclass


@dataclass
class Violation:
    rule_id: str
    severity: str          # CRITICAL | WARNING | INFO
    table: str
    identifier: str        # e.g. "TCS / 2024-03"
    message: str


# ── DQ-01 : Company PK uniqueness ──────────────────────────────────
def check_company_pk_uniqueness(company_ids: list) -> list[str]:
    """Returns list of duplicate ids (empty list = pass)."""
    seen, dupes = set(), []
    for cid in company_ids:
        if cid in seen:
            dupes.append(cid)
        seen.add(cid)
    return dupes


# ── DQ-02 : Annual PK uniqueness (company_id, year) ────────────────
def find_duplicate_period_keys(rows: list[tuple]) -> list[tuple]:
    """rows: list of (company_id, year). Returns duplicated keys."""
    seen, dupes = set(), []
    for key in rows:
        if key in seen:
            dupes.append(key)
        seen.add(key)
    return dupes


# ── DQ-03 : FK integrity ───────────────────────────────────────────
def find_orphan_fk(child_company_ids: set, valid_company_ids: set) -> set:
    return child_company_ids - valid_company_ids


# ── DQ-04 : Balance sheet must balance (assets == liabilities) ─────
def check_bs_balance(total_assets, total_liabilities, tolerance=0.01) -> bool:
    """True = PASSES (within tolerance). Guards against divide-by-zero."""
    if total_assets in (None, 0):
        return False
    return abs(total_assets - total_liabilities) / abs(total_assets) < tolerance


# ── DQ-05 : OPM cross-check ─────────────────────────────────────────
def check_opm_crosscheck(opm_percentage, operating_profit, sales, tolerance=1.0) -> bool:
    if not sales:
        return False
    computed = (operating_profit / sales) * 100
    return abs(opm_percentage - computed) < tolerance


# ── DQ-06 : Positive sales ─────────────────────────────────────────
def check_positive_sales(sales) -> bool:
    return sales is not None and sales > 0


# ── DQ-07 : Year format (post-normalisation) ────────────────────────
import re
_YEAR_FMT_RE = re.compile(r"^\d{4}-\d{2}$")


def check_year_format(normalised_year) -> bool:
    return bool(normalised_year) and bool(_YEAR_FMT_RE.match(normalised_year))


# ── DQ-08 : Ticker format ───────────────────────────────────────────
def check_ticker_format(normalised_ticker) -> bool:
    return normalised_ticker is not None and 2 <= len(normalised_ticker) <= 12


# ── DQ-09 : Net cash flow reconciliation ────────────────────────────
def check_net_cash(net_cash_flow, cfo, cfi, cff, tolerance_cr=10) -> bool:
    if None in (net_cash_flow, cfo, cfi, cff):
        return False
    return abs(net_cash_flow - (cfo + cfi + cff)) <= tolerance_cr


# ── DQ-10 : Non-negative fixed assets ───────────────────────────────
def coerce_nonneg_fixed_assets(fixed_assets):
    """Returns (corrected_value, was_flagged)."""
    if fixed_assets is not None and fixed_assets < 0:
        return 0, True
    return fixed_assets, False


# ── DQ-11 : Tax rate range ──────────────────────────────────────────
def check_tax_rate_range(tax_percentage, lo=0, hi=60) -> bool:
    return tax_percentage is None or (lo <= tax_percentage <= hi)


# ── DQ-12 : Dividend payout cap ─────────────────────────────────────
def check_dividend_payout(dividend_payout, cap=200) -> bool:
    return dividend_payout is None or dividend_payout <= cap


# ── DQ-13 : URL validity (documents) ────────────────────────────────
# NOTE: performing live HTTP HEAD requests against ~1,585 URLs during
# every `make load` would be slow and flaky (network-dependent). We
# expose the check function (used by tests + an optional standalone
# `validate_urls` pass) but do NOT call it automatically during load.
def check_url_reachable(url: str, timeout=5) -> bool:
    import urllib.request
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


# ── DQ-14 : EPS sign consistency ────────────────────────────────────
def check_eps_sign(eps, net_profit) -> bool:
    if eps is None or net_profit is None:
        return True  # can't judge, don't flag
    if net_profit > 0:
        return eps > 0
    return True


# ── DQ-15 : strict BS balance (informational only) ──────────────────
def check_bs_strict_balance(total_assets, total_liabilities) -> bool:
    return total_assets == total_liabilities


# ── DQ-16 : coverage check (>= 5 years of history per company) ─────
def check_coverage(years_present: int, minimum=5) -> bool:
    return years_present >= minimum


# Aliases for test compatibility (tests/dq/test_rules.py expects validate_* functions)
validate_company_pk = check_company_pk_uniqueness
validate_annual_pk = find_duplicate_period_keys
validate_fk_integrity = find_orphan_fk
validate_bs_balance = check_bs_balance
validate_opm_cross_check = check_opm_crosscheck
validate_positive_sales = check_positive_sales
validate_year_format = check_year_format
validate_ticker_format = check_ticker_format
validate_net_cash = check_net_cash
validate_fixed_assets = coerce_nonneg_fixed_assets
validate_tax_rate = check_tax_rate_range
validate_dividend_payout = check_dividend_payout
validate_eps_sign = check_eps_sign
validate_coverage = check_coverage
