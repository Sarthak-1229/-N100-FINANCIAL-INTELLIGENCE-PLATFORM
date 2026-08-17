"""tests/etl/test_normaliser_helpers.py"""
from src.etl.normaliser import normalize_numeric, parse_analysis_metric


class TestNormalizeNumeric:
    def test_plain_int(self):
        assert normalize_numeric(100) == 100.0

    def test_plain_float(self):
        assert normalize_numeric(3.14) == 3.14

    def test_string_number(self):
        assert normalize_numeric("42.5") == 42.5

    def test_string_with_commas(self):
        assert normalize_numeric("1,234.5") == 1234.5

    def test_none_returns_none(self):
        assert normalize_numeric(None) is None

    def test_na_string_returns_none(self):
        assert normalize_numeric("NA") is None
        assert normalize_numeric("N/A") is None

    def test_dash_returns_none(self):
        assert normalize_numeric("-") is None

    def test_garbage_returns_none(self):
        assert normalize_numeric("abc") is None

    def test_nan_float_returns_none(self):
        assert normalize_numeric(float("nan")) is None


class TestParseAnalysisMetric:
    def test_ten_years_format(self):
        period, value = parse_analysis_metric("10 Years: 21%")
        assert period == 10 and value == 21.0

    def test_extra_whitespace(self):
        period, value = parse_analysis_metric("5 Years          14%")
        assert period == 5 and value == 14.0

    def test_negative_value(self):
        period, value = parse_analysis_metric("3 Years: -7%")
        assert period == 3 and value == -7.0

    def test_none_input(self):
        period, value = parse_analysis_metric(None)
        assert period is None and value is None

    def test_no_percent_sign(self):
        period, value = parse_analysis_metric("10 Years")
        assert period == 10 and value is None
