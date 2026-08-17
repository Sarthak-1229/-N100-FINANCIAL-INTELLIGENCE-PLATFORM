"""tests/etl/test_normaliser_year.py — 20+ tests for normalize_year()"""
import pytest
from src.etl.normaliser import normalize_year


class TestMonthYearFormat:
    def test_standard_mar_format(self):
        assert normalize_year("Mar 2024") == "2024-03"

    def test_standard_dec_format(self):
        assert normalize_year("Dec 2012") == "2012-12"

    def test_standard_jun_format(self):
        assert normalize_year("Jun 2013") == "2013-06"

    def test_standard_sep_format(self):
        assert normalize_year("Sep 2011") == "2011-09"

    def test_dash_format_two_digit_year(self):
        assert normalize_year("Mar-13") == "2013-03"

    def test_dash_format_all_months(self):
        assert normalize_year("Mar-24") == "2024-03"

    def test_case_insensitive_month(self):
        assert normalize_year("mar 2024") == "2024-03"
        assert normalize_year("MAR 2024") == "2024-03"

    def test_trailing_junk_9m_ignored(self):
        assert normalize_year("Mar 2016 9m") == "2016-03"

    def test_trailing_junk_number_ignored(self):
        assert normalize_year("Mar 2023 15") == "2023-03"

    def test_leading_trailing_whitespace(self):
        assert normalize_year("  Mar 2024  ") == "2024-03"


class TestBareYearFormat:
    def test_bare_year_defaults_to_march(self):
        assert normalize_year("2013") == "2013-03"

    def test_bare_year_with_fraction(self):
        assert normalize_year("2024.5") == "2024-03"

    def test_bare_year_out_of_range_rejected(self):
        assert normalize_year("1850") is None

    def test_bare_year_default_disabled(self):
        assert normalize_year("2013", assume_default_month=False) is None


class TestUnparseableValues:
    def test_ttm_rejected(self):
        assert normalize_year("TTM") is None

    def test_ttm_lowercase_rejected(self):
        assert normalize_year("ttm") is None

    def test_none_rejected(self):
        assert normalize_year(None) is None

    def test_empty_string_rejected(self):
        assert normalize_year("") is None

    def test_na_rejected(self):
        assert normalize_year("N/A") is None
        assert normalize_year("NA") is None

    def test_garbage_text_rejected(self):
        assert normalize_year("not a year") is None

    def test_invalid_month_abbreviation_rejected(self):
        assert normalize_year("Xyz 2024") is None


class TestOutputFormat:
    def test_output_matches_dq07_regex(self):
        import re
        result = normalize_year("Mar 2024")
        assert re.match(r"^\d{4}-\d{2}$", result)

    def test_two_digit_month_always_zero_padded(self):
        assert normalize_year("Jan 2020") == "2020-01"  # not '2020-1'
