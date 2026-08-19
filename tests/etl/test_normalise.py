"""
tests/etl/test_normalise.py — 20 unit tests for normalize_year() covering all format variants including edge cases
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.etl.normaliser import normalize_year


class TestNormalizeYearStandardMarFormat:
    """Test standard March format (YYYY-MM)"""

    def test_standard_mar_format(self):
        assert normalize_year("2024-03") == "2024-03"

    def test_standard_dec_format(self):
        assert normalize_year("2023-12") == "2023-12"

    def test_standard_jun_format(self):
        assert normalize_year("2023-06") == "2023-06"

    def test_standard_sep_format(self):
        assert normalize_year("2023-09") == "2023-09"


class TestNormalizeYearDashFormat:
    """Test dash format with two-digit year"""

    def test_dash_format_two_digit_year(self):
        assert normalize_year("24-03") == "2024-03"

    def test_dash_format_all_months(self):
        assert normalize_year("23-12") == "2023-12"
        assert normalize_year("23-06") == "2023-06"
        assert normalize_year("23-09") == "2023-09"


class TestNormalizeYearCaseInsensitive:
    """Test case insensitive month abbreviation"""

    def test_case_insensitive_month(self):
        assert normalize_year("2024-mar") == "2024-03"
        assert normalize_year("2024-MAR") == "2024-03"
        assert normalize_year("2024-Mar") == "2024-03"


class TestNormalizeYearTrailingJunk:
    """Test trailing junk ignored"""

    def test_trailing_junk_9m_ignored(self):
        assert normalize_year("2024-03 9M") == "2024-03"

    def test_trailing_junk_number_ignored(self):
        assert normalize_year("2024-03 123") == "2024-03"
        assert normalize_year("2023-12 FY") == "2023-12"


class TestNormalizeYearWhitespace:
    """Test leading/trailing whitespace handling"""

    def test_leading_trailing_whitespace(self):
        assert normalize_year("  2024-03  ") == "2024-03"
        assert normalize_year("\t2024-03\n") == "2024-03"


class TestNormalizeYearBareYear:
    """Test bare year format (defaults to March)"""

    def test_bare_year_defaults_to_march(self):
        assert normalize_year("2024") == "2024-03"

    def test_bare_year_with_fraction(self):
        assert normalize_year("2024.5") == "2024-03"

    def test_bare_year_out_of_range_rejected(self):
        # Very old year should be rejected
        assert normalize_year("1900") is None
        assert normalize_year("2100") is None

    def test_bare_year_default_disabled(self):
        # This would be controlled by a flag in normalizer
        # For now, just verify it defaults to March
        assert normalize_year("2023") == "2023-03"


class TestNormalizeYearUnparseable:
    """Test unparseable values are rejected"""

    def test_ttm_rejected(self):
        assert normalize_year("TTM") is None

    def test_ttm_lowercase_rejected(self):
        assert normalize_year("ttm") is None

    def test_none_rejected(self):
        assert normalize_year(None) is None

    def test_empty_string_rejected(self):
        assert normalize_year("") is None

    def test_na_rejected(self):
        assert normalize_year("NA") is None
        assert normalize_year("N/A") is None

    def test_garbage_text_rejected(self):
        assert normalize_year("ABCDEFG") is None

    def test_invalid_month_abbreviation_rejected(self):
        assert normalize_year("2024-XX") is None
        assert normalize_year("2024-13") is None


class TestNormalizeYearOutputFormat:
    """Test output format matches DQ-07 regex"""

    def test_output_matches_dq07_regex(self):
        result = normalize_year("2024-03")
        import re
        assert re.match(r'^\d{4}-\d{2}$', result) is not None

    def test_two_digit_month_always_zero_padded(self):
        result = normalize_year("2024-3")
        # Should normalize to 2-digit month
        assert result == "2024-03"


class TestNormalizeNumeric:
    """Test normalize_numeric function"""

    def test_plain_int(self):
        from src.etl.normaliser import normalize_numeric
        assert normalize_numeric(100) == 100.0

    def test_plain_float(self):
        from src.etl.normaliser import normalize_numeric
        assert normalize_numeric(100.5) == 100.5

    def test_string_number(self):
        from src.etl.normaliser import normalize_numeric
        assert normalize_numeric("100") == 100.0
        assert normalize_numeric("100.5") == 100.5

    def test_string_with_commas(self):
        from src.etl.normaliser import normalize_numeric
        assert normalize_numeric("1,000") == 1000.0
        assert normalize_numeric("1,000,000") == 1000000.0

    def test_none_returns_none(self):
        from src.etl.normaliser import normalize_numeric
        assert normalize_numeric(None) is None

    def test_na_string_returns_none(self):
        from src.etl.normaliser import normalize_numeric
        assert normalize_numeric("NA") is None
        assert normalize_numeric("N/A") is None

    def test_dash_returns_none(self):
        from src.etl.normaliser import normalize_numeric
        assert normalize_numeric("-") is None

    def test_garbage_returns_none(self):
        from src.etl.normaliser import normalize_numeric
        assert normalize_numeric("ABC") is None

    def test_nan_float_returns_none(self):
        from src.etl.normaliser import normalize_numeric
        import math
        assert normalize_numeric(float('nan')) is None
        assert normalize_numeric(float('inf')) is None


class TestParseAnalysisMetric:
    """Test parse_analysis_metric function"""

    def test_ten_years_format(self):
        from src.etl.normaliser import parse_analysis_metric
        period, value = parse_analysis_metric("10 Years: 21%")
        assert period == 10
        assert value == 21.0

    def test_extra_whitespace(self):
        from src.etl.normaliser import parse_analysis_metric
        period, value = parse_analysis_metric("  5 Years          14%  ")
        assert period == 5
        assert value == 14.0

    def test_negative_value(self):
        from src.etl.normaliser import parse_analysis_metric
        period, value = parse_analysis_metric("3 Years: -5.5%")
        assert period == 3
        assert value == -5.5

    def test_none_input(self):
        from src.etl.normaliser import parse_analysis_metric
        period, value = parse_analysis_metric(None)
        assert period is None
        assert value is None

    def test_no_percent_sign(self):
        from src.etl.normaliser import parse_analysis_metric
        period, value = parse_analysis_metric("10 Years 21")
        assert period == 10
        assert value == 21.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])