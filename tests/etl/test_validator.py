"""tests/etl/test_validator.py — tests for the DQ-01..DQ-16 rule functions"""
from src.etl import validator as dq


class TestDQ01CompanyPK:
    def test_no_duplicates_passes(self):
        assert dq.check_company_pk_uniqueness(["TCS", "INFY", "WIPRO"]) == []

    def test_duplicate_detected(self):
        assert dq.check_company_pk_uniqueness(["TCS", "TCS", "INFY"]) == ["TCS"]


class TestDQ02AnnualPK:
    def test_no_duplicates(self):
        rows = [("TCS", "2024-03"), ("TCS", "2023-03")]
        assert dq.find_duplicate_period_keys(rows) == []

    def test_duplicate_key_detected(self):
        rows = [("TCS", "2024-03"), ("TCS", "2024-03")]
        assert dq.find_duplicate_period_keys(rows) == [("TCS", "2024-03")]


class TestDQ03FKIntegrity:
    def test_no_orphans(self):
        assert dq.find_orphan_fk({"TCS", "INFY"}, {"TCS", "INFY", "WIPRO"}) == set()

    def test_orphan_detected(self):
        assert dq.find_orphan_fk({"TCS", "FAKECO"}, {"TCS", "INFY"}) == {"FAKECO"}


class TestDQ04BSBalance:
    def test_balanced_sheet_passes(self):
        assert dq.check_bs_balance(1000, 1000) is True

    def test_within_tolerance_passes(self):
        # spec example: assets=1000, liab=1020 -> 2% diff -> should trigger WARNING (fail)
        assert dq.check_bs_balance(1000, 1005) is True  # 0.5% within 1% tolerance

    def test_spec_example_dq04_triggers(self):
        # from the spec's own test table: assets=1000, liab=1020 -> WARNING
        assert dq.check_bs_balance(1000, 1020) is False

    def test_zero_assets_fails_safely(self):
        assert dq.check_bs_balance(0, 500) is False

    def test_none_assets_fails_safely(self):
        assert dq.check_bs_balance(None, 500) is False


class TestDQ05OPMCrossCheck:
    def test_matching_opm_passes(self):
        # operating_profit=200, sales=1000 -> computed OPM = 20%
        assert dq.check_opm_crosscheck(20.0, 200, 1000) is True

    def test_mismatched_opm_fails(self):
        assert dq.check_opm_crosscheck(30.0, 200, 1000) is False

    def test_zero_sales_fails_safely(self):
        assert dq.check_opm_crosscheck(20.0, 200, 0) is False


class TestDQ06PositiveSales:
    def test_positive_sales_passes(self):
        assert dq.check_positive_sales(1000) is True

    def test_spec_example_zero_sales_triggers_warning(self):
        assert dq.check_positive_sales(0) is False

    def test_negative_sales_fails(self):
        assert dq.check_positive_sales(-100) is False

    def test_none_sales_fails(self):
        assert dq.check_positive_sales(None) is False


class TestDQ07YearFormat:
    def test_valid_format_passes(self):
        assert dq.check_year_format("2024-03") is True

    def test_missing_dash_fails(self):
        assert dq.check_year_format("202403") is False

    def test_none_fails(self):
        assert dq.check_year_format(None) is False


class TestDQ08TickerFormat:
    def test_valid_ticker_passes(self):
        assert dq.check_ticker_format("TCS") is True

    def test_none_fails(self):
        assert dq.check_ticker_format(None) is False

    def test_too_short_fails(self):
        assert dq.check_ticker_format("A") is False


class TestDQ09NetCash:
    def test_reconciling_values_pass(self):
        assert dq.check_net_cash(100, 60, -20, 60) is True  # 60-20+60=100

    def test_within_tolerance_passes(self):
        assert dq.check_net_cash(105, 60, -20, 60) is True  # off by 5, tolerance=10

    def test_outside_tolerance_fails(self):
        assert dq.check_net_cash(150, 60, -20, 60) is False  # off by 50

    def test_missing_component_fails_safely(self):
        assert dq.check_net_cash(100, None, -20, 60) is False


class TestDQ10FixedAssets:
    def test_positive_value_unchanged(self):
        value, flagged = dq.coerce_nonneg_fixed_assets(500)
        assert value == 500 and flagged is False

    def test_negative_value_coerced_to_zero(self):
        value, flagged = dq.coerce_nonneg_fixed_assets(-50)
        assert value == 0 and flagged is True


class TestDQ11TaxRate:
    def test_normal_rate_passes(self):
        assert dq.check_tax_rate_range(25.0) is True

    def test_zero_rate_passes_boundary(self):
        assert dq.check_tax_rate_range(0) is True

    def test_sixty_percent_passes_boundary(self):
        assert dq.check_tax_rate_range(60) is True

    def test_over_sixty_fails(self):
        assert dq.check_tax_rate_range(75.0) is False

    def test_negative_fails(self):
        assert dq.check_tax_rate_range(-5.0) is False

    def test_none_treated_as_pass(self):
        assert dq.check_tax_rate_range(None) is True


class TestDQ12DividendPayout:
    def test_normal_payout_passes(self):
        assert dq.check_dividend_payout(50.0) is True

    def test_boundary_200_passes(self):
        assert dq.check_dividend_payout(200) is True

    def test_over_200_fails(self):
        assert dq.check_dividend_payout(250.0) is False


class TestDQ14EPSSign:
    def test_positive_profit_positive_eps_passes(self):
        assert dq.check_eps_sign(5.0, 1000) is True

    def test_positive_profit_negative_eps_fails(self):
        assert dq.check_eps_sign(-5.0, 1000) is False

    def test_negative_profit_any_eps_passes(self):
        assert dq.check_eps_sign(-5.0, -1000) is True

    def test_missing_values_pass_by_default(self):
        assert dq.check_eps_sign(None, 1000) is True


class TestDQ16Coverage:
    def test_sufficient_years_passes(self):
        assert dq.check_coverage(10) is True

    def test_exactly_minimum_passes(self):
        assert dq.check_coverage(5) is True

    def test_below_minimum_fails(self):
        assert dq.check_coverage(3) is False
