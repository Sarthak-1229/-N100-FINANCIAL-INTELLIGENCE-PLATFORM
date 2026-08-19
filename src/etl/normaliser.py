"""
src/etl/normaliser.py

Pure, side-effect-free functions that turn messy raw Excel values into
canonical forms. "Pure" means: same input always gives same output, no
file/DB access, no printing. That's what makes these trivial to unit test.

Two functions the spec calls out by name:
    normalize_year(raw)   -> 'YYYY-MM' string, or None if unparseable
    normalize_ticker(raw) -> uppercase, trimmed ticker, or None if invalid
"""
import re

_MONTHS = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
    "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
    "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
}

# Matches "Mar 2024", "Mar-24", "Dec 2012", "Mar 2016 9m", "Mar 2023 15"
# group(1) = 3-letter month, group(2) = 2 or 4 digit year (trailing junk ignored)
_MONTH_YEAR_RE = re.compile(
    r"^([A-Za-z]{3})[\s\-](\d{2,4})", re.IGNORECASE
)

# Matches "2024-03", "24-03", "2023-12", "23-12" etc. (year-month format)
# group(1) = year (2 or 4 digits), group(2) = month (1 or 2 digits)
# Allows optional trailing whitespace and text (junk ignored)
_ISO_YEAR_MONTH_RE = re.compile(r"^(\d{2,4})-(\d{1,2})")

# Matches a bare year like "2013" or "2024.5" (fractional part ignored)
_BARE_YEAR_RE = re.compile(r"^(\d{4})(\.\d+)?$")

# Matches "2024-mar", "24-mar", etc. (year-month with month letters)
# group(1) = year (2 or 4 digits), group(2) = 3-letter month
_YEAR_MONTH_RE = re.compile(r"^(\d{2,4})[\s\-]([A-Za-z]{3})", re.IGNORECASE)

# Values that are explicitly not a fiscal year-end and must be rejected
_UNPARSEABLE = {"TTM", "N/A", "NA", "", "NAN"}

DEFAULT_FISCAL_MONTH = "03"  # March: the modal fiscal year-end in this dataset


def normalize_year(raw, assume_default_month: bool = True):
    """
    Convert a messy raw year string into canonical 'YYYY-MM' form.

    Examples
    --------
    'Mar 2024'      -> '2024-03'
    'Mar-24'        -> '2024-03'
    'Dec 2012'      -> '2012-12'
    'Mar 2016 9m'   -> '2016-03'   (trailing '9m' junk ignored)
    '2013'          -> '2013-03'  if assume_default_month else None
    'TTM'           -> None       (not a real fiscal period -> reject)
    None / ''       -> None

    Returns
    -------
    str | None : 'YYYY-MM', or None if the value can't be parsed
        (caller is responsible for logging rejected rows -- DQ-07)
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if text.upper() in _UNPARSEABLE:
        return None

    # First, try to match ISO format: YYYY-MM or YY-MM etc. (with optional trailing junk)
    m = _ISO_YEAR_MONTH_RE.match(text)
    if m:
        year_digits = m.group(1)
        month_digits = m.group(2)
        year = _expand_two_digit_year(year_digits)
        if year is None:
            return None
        month = int(month_digits)
        if not (1 <= month <= 12):
            return None
        # Zero-pad month to 2 digits
        return f"{year}-{month:02d}"

    # Second, try to match year-month with month letters (e.g., "2024-mar") with optional trailing junk
    m = _YEAR_MONTH_RE.match(text)
    if m:
        year_digits = m.group(1)
        month_abbr = m.group(2).upper()
        if month_abbr not in _MONTHS:
            return None
        year = _expand_two_digit_year(year_digits)
        if year is None:
            return None
        month = _MONTHS[month_abbr]
        return f"{year}-{month}"

    # Third, try to match month-year format (e.g., "Mar 2024") with optional trailing junk
    m = _MONTH_YEAR_RE.match(text)
    if m:
        month_abbr = m.group(1).upper()
        year_digits = m.group(2)
        if month_abbr not in _MONTHS:
            return None
        month = _MONTHS[month_abbr]
        year = _expand_two_digit_year(year_digits)
        if year is None:
            return None
        return f"{year}-{month}"

    m = _BARE_YEAR_RE.match(text)
    if m:
        if not assume_default_month:
            return None
        year = int(m.group(1))
        if not (1990 <= year <= 2035):
            return None
        return f"{year}-{DEFAULT_FISCAL_MONTH}"

    return None


def _expand_two_digit_year(year_digits: str):
    """'24' -> 2024, '13' -> 2013, '2024' -> 2024. Rejects nonsense."""
    if len(year_digits) == 4:
        year = int(year_digits)
    elif len(year_digits) == 2:
        year = 2000 + int(year_digits)
    else:
        return None
    if not (1990 <= year <= 2035):
        return None
    return year


def normalize_ticker(raw):
    """
    Canonical ticker form per DQ-08: strip whitespace, uppercase,
    length must be 2-12 characters.

    Examples
    --------
    ' tcs '        -> 'TCS'
    'reliance'     -> 'RELIANCE'
    'bajaj-auto'   -> 'BAJAJ-AUTO'
    ''             -> None
    'A'            -> None   (too short, likely a data error)
    'THISISWAYTOOLONGATICKER' -> None  (too long)

    Returns
    -------
    str | None
    """
    if raw is None:
        return None
    ticker = str(raw).strip().upper()
    if not (2 <= len(ticker) <= 12):
        return None
    return ticker


def normalize_numeric(raw):
    """
    Coerce a raw cell to float, treating common 'missing value' spellings
    ('', 'NA', 'N/A', '-', 'nan') as None rather than raising an error.
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        import math
        if math.isnan(raw) or math.isinf(raw):
            return None
        return float(raw)
    text = str(raw).strip()
    if text.upper() in {"", "NA", "N/A", "-", "NAN"}:
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def parse_analysis_metric(raw):
    """
    The `analysis` table smashes a period and a percentage into one text
    cell, e.g. '10 Years:     21%' or '5 Years          14%'.
    Returns (period_years: int | None, value_pct: float | None).
    """
    if raw is None:
        return None, None
    text = str(raw)
    period_match = re.search(r"(\d+)\s*Years?", text, re.IGNORECASE)
    if period_match:
        # Start looking for the value after the period match
        start_pos = period_match.end()
        value_match = re.search(r"(-?\d+(?:\.\d+)?)\s*%?", text[start_pos:])
    else:
        period_match = None
        value_match = None
    period = int(period_match.group(1)) if period_match else None
    value = float(value_match.group(1)) if value_match else None
    return period, value
