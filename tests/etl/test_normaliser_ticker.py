"""tests/etl/test_normaliser_ticker.py — 15+ tests for normalize_ticker()"""
from src.etl.normaliser import normalize_ticker


class TestValidTickers:
    def test_already_clean_ticker_unchanged(self):
        assert normalize_ticker("TCS") == "TCS"

    def test_lowercase_gets_uppercased(self):
        assert normalize_ticker("reliance") == "RELIANCE"

    def test_mixed_case_gets_uppercased(self):
        assert normalize_ticker("TaTaMoToRs") == "TATAMOTORS"

    def test_leading_trailing_whitespace_stripped(self):
        assert normalize_ticker("  TCS  ") == "TCS"

    def test_hyphenated_ticker_preserved(self):
        assert normalize_ticker("bajaj-auto") == "BAJAJ-AUTO"

    def test_ampersand_ticker_preserved(self):
        assert normalize_ticker("m&m") == "M&M"

    def test_two_char_ticker_is_valid_minimum(self):
        assert normalize_ticker("AB") == "AB"

    def test_twelve_char_ticker_is_valid_maximum(self):
        assert normalize_ticker("ABCDEFGHIJKL") == "ABCDEFGHIJKL"


class TestInvalidTickers:
    def test_none_rejected(self):
        assert normalize_ticker(None) is None

    def test_empty_string_rejected(self):
        assert normalize_ticker("") is None

    def test_whitespace_only_rejected(self):
        assert normalize_ticker("   ") is None

    def test_single_char_too_short(self):
        assert normalize_ticker("A") is None

    def test_thirteen_chars_too_long(self):
        assert normalize_ticker("ABCDEFGHIJKLM") is None

    def test_way_too_long_rejected(self):
        assert normalize_ticker("THISISWAYTOOLONGATICKERNAME") is None


class TestRealDataTickers:
    """Regression tests using actual tickers seen in the source files."""
    def test_adanigreen(self):
        assert normalize_ticker("ADANIGREEN") == "ADANIGREEN"

    def test_hdfcbank(self):
        assert normalize_ticker("HDFCBANK") == "HDFCBANK"

    def test_orphan_ticker_still_normalises_even_though_not_in_companies(self):
        # normalize_ticker only checks FORMAT (DQ-08); it doesn't know
        # about the companies table. FK checking (DQ-03) is a separate
        # concern handled by the loader, not this function.
        assert normalize_ticker("wipro") == "WIPRO"
