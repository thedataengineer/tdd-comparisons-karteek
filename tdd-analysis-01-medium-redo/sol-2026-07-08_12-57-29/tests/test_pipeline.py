"""Tests for the full pipeline (run_pipeline)."""

import pytest
from report_pipeline.pipeline import run_pipeline
from report_pipeline.parse import ParseError
from report_pipeline.validate import ValidationError


# ── Happy-path tests ──────────────────────────────────────────────────────────

class TestRunPipelineSuccess:
    def test_single_row_returns_string(self):
        result = run_pipeline(["1:REVENUE:1000.00:2024-Q1"])
        assert isinstance(result, str)

    def test_table_contains_period(self):
        result = run_pipeline(["1:REVENUE:500.00:2024-Q2"])
        assert "2024-Q2" in result

    def test_table_contains_category(self):
        result = run_pipeline(["1:REVENUE:500.00:2024-Q1"])
        assert "REVENUE" in result

    def test_table_contains_total_column(self):
        result = run_pipeline(["1:REVENUE:500.00:2024-Q1"])
        assert "TOTAL" in result

    def test_multiple_rows_multiple_periods(self):
        raw = [
            "1:REVENUE:1000.00:2024-Q1",
            "2:REVENUE:2000.00:2024-Q2",
            "3:COST:-500.00:2024-Q1",
            "4:COST:-300.00:2024-Q2",
            "5:HEADCOUNT:10:2024-Q1",
            "6:HEADCOUNT:12:2024-Q2",
        ]
        result = run_pipeline(raw)
        assert isinstance(result, str)
        assert "2024-Q1" in result
        assert "2024-Q2" in result
        assert "REVENUE" in result
        assert "COST" in result
        assert "HEADCOUNT" in result

    def test_monetary_formatting_in_output(self):
        result = run_pipeline(["1:REVENUE:1234.56:2024-Q1"])
        assert "$1,234.56" in result

    def test_negative_cost_formatted(self):
        result = run_pipeline(["1:COST:-200.00:2024-Q1"])
        assert "-$200.00" in result

    def test_headcount_as_plain_integer(self):
        result = run_pipeline(["1:HEADCOUNT:42:2024-Q1"])
        # Headcount should appear as plain int (no $)
        lines = result.split("\n")
        hc_line = next(l for l in lines if "HEADCOUNT" in l)
        assert "$" not in hc_line[len("HEADCOUNT"):]

    def test_total_row_present(self):
        result = run_pipeline(["1:REVENUE:100:2024-Q1"])
        lines = result.split("\n")
        assert any(l.startswith("TOTAL") for l in lines)

    def test_empty_input_returns_string(self):
        # Empty input: aggregate returns empty AggregatedData → table is just header+total
        result = run_pipeline([])
        assert isinstance(result, str)

    def test_periods_chronological(self):
        raw = [
            "1:REVENUE:100:2024-Q3",
            "2:REVENUE:200:2024-Q1",
        ]
        result = run_pipeline(raw)
        header = result.split("\n")[0]
        assert header.index("2024-Q1") < header.index("2024-Q3")

    def test_full_four_quarter_report(self):
        raw = [f"{i}:REVENUE:{i * 100}:2024-Q{i}" for i in range(1, 5)]
        result = run_pipeline(raw)
        for q in range(1, 5):
            assert f"2024-Q{q}" in result
        # Total revenue = 100+200+300+400 = 1000
        assert "$1,000.00" in result


# ── Parse-error propagation ───────────────────────────────────────────────────

class TestRunPipelineParseErrors:
    def test_bad_field_count_returns_parse_error(self):
        result = run_pipeline(["1:REVENUE:100"])
        assert isinstance(result, ParseError)
        assert result.stage == "parse"

    def test_invalid_category_returns_parse_error(self):
        result = run_pipeline(["1:PROFIT:100:2024-Q1"])
        assert isinstance(result, ParseError)

    def test_negative_revenue_returns_parse_error(self):
        result = run_pipeline(["1:REVENUE:-100:2024-Q1"])
        assert isinstance(result, ParseError)

    def test_invalid_period_returns_parse_error(self):
        result = run_pipeline(["1:REVENUE:100:2024-Q9"])
        assert isinstance(result, ParseError)

    def test_duplicate_row_id_returns_parse_error(self):
        result = run_pipeline([
            "1:REVENUE:100:2024-Q1",
            "1:COST:-50:2024-Q1",
        ])
        assert isinstance(result, ParseError)

    def test_error_contains_bad_string(self):
        bad = "1:BAD_CAT:100:2024-Q1"
        result = run_pipeline([bad])
        assert isinstance(result, ParseError)
        assert result.raw == bad

    def test_first_bad_string_reported(self):
        result = run_pipeline([
            "1:REVENUE:100:2024-Q1",
            "2:REVENUE:-50:2024-Q1",  # invalid
            "3:COST:-10:2024-Q1",
        ])
        assert isinstance(result, ParseError)
        assert result.raw == "2:REVENUE:-50:2024-Q1"
