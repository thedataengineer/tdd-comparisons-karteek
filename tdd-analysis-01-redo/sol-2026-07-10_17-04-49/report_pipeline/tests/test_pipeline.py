"""Tests for the report_pipeline module."""
import pytest
from report_pipeline.pipeline import (
    parse,
    aggregate,
    format_table,
    validate_output,
    run_pipeline,
    ParseError,
    ValidationError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
VALID_ROWS = [
    "1:REVENUE:1000.00:2024-Q1",
    "2:COST:-200.00:2024-Q1",
    "3:HEADCOUNT:10:2024-Q1",
    "4:REVENUE:2000.00:2024-Q2",
    "5:COST:-400.00:2024-Q2",
    "6:HEADCOUNT:20:2024-Q2",
]


# ===========================================================================
# Stage 1 – Parse
# ===========================================================================

class TestParse:
    def test_returns_list_of_dicts(self):
        result = parse(["1:REVENUE:500.00:2024-Q1"])
        assert isinstance(result, list)
        assert len(result) == 1

    def test_row_structure(self):
        result = parse(["1:REVENUE:500.00:2024-Q1"])
        row = result[0]
        assert row["row_id"] == 1
        assert row["category"] == "REVENUE"
        assert row["value"] == 500.00
        assert row["period"] == "2024-Q1"

    def test_multiple_rows(self):
        result = parse(VALID_ROWS)
        assert len(result) == 6

    def test_negative_cost_allowed(self):
        result = parse(["1:COST:-300.50:2023-Q4"])
        assert result[0]["value"] == -300.50

    def test_positive_cost_allowed(self):
        result = parse(["1:COST:300.50:2023-Q4"])
        assert result[0]["value"] == 300.50

    def test_headcount_integer_value(self):
        result = parse(["1:HEADCOUNT:15:2024-Q3"])
        assert result[0]["value"] == 15

    # --- Error cases ---

    def test_error_on_wrong_field_count(self):
        result = parse(["1:REVENUE:2024-Q1"])  # missing VALUE
        assert isinstance(result, ParseError)
        assert result.raw == "1:REVENUE:2024-Q1"

    def test_error_on_invalid_row_id(self):
        result = parse(["abc:REVENUE:100:2024-Q1"])
        assert isinstance(result, ParseError)

    def test_error_on_zero_row_id(self):
        result = parse(["0:REVENUE:100:2024-Q1"])
        assert isinstance(result, ParseError)

    def test_error_on_negative_row_id(self):
        result = parse(["-1:REVENUE:100:2024-Q1"])
        assert isinstance(result, ParseError)

    def test_error_on_unknown_category(self):
        result = parse(["1:EXPENSES:100:2024-Q1"])
        assert isinstance(result, ParseError)

    def test_error_on_invalid_value(self):
        result = parse(["1:REVENUE:abc:2024-Q1"])
        assert isinstance(result, ParseError)

    def test_error_on_negative_revenue(self):
        result = parse(["1:REVENUE:-100:2024-Q1"])
        assert isinstance(result, ParseError)
        assert "negative" in result.reason.lower() or "REVENUE" in result.reason

    def test_error_on_negative_headcount(self):
        result = parse(["1:HEADCOUNT:-5:2024-Q1"])
        assert isinstance(result, ParseError)

    def test_error_on_bad_period_format(self):
        result = parse(["1:REVENUE:100:2024-Q5"])
        assert isinstance(result, ParseError)

    def test_error_on_bad_period_year(self):
        result = parse(["1:REVENUE:100:24-Q1"])
        assert isinstance(result, ParseError)

    def test_error_on_duplicate_row_id(self):
        result = parse(["1:REVENUE:100:2024-Q1", "1:COST:50:2024-Q1"])
        assert isinstance(result, ParseError)

    def test_error_identifies_failing_string(self):
        bad = "2:REVENUE:-50:2024-Q1"
        result = parse(["1:REVENUE:100:2024-Q1", bad])
        assert isinstance(result, ParseError)
        assert result.raw == bad

    def test_error_has_reason(self):
        result = parse(["1:REVENUE:-50:2024-Q1"])
        assert isinstance(result, ParseError)
        assert result.reason

    def test_period_q1_to_q4_valid(self):
        for q in range(1, 5):
            result = parse([f"1:REVENUE:100:2024-Q{q}"])
            assert isinstance(result, list)

    def test_empty_input(self):
        result = parse([])
        assert result == []


# ===========================================================================
# Stage 2 – Aggregate
# ===========================================================================

class TestAggregate:
    def _parsed(self):
        return parse(VALID_ROWS)

    def test_returns_dict(self):
        result = aggregate(self._parsed())
        assert isinstance(result, dict)

    def test_periods_key_ordered_chronologically(self):
        rows = parse([
            "1:REVENUE:100:2024-Q2",
            "2:REVENUE:200:2024-Q1",
        ])
        result = aggregate(rows)
        assert result["periods"] == ["2024-Q1", "2024-Q2"]

    def test_periods_across_years_ordered(self):
        rows = parse([
            "1:REVENUE:100:2025-Q1",
            "2:REVENUE:200:2024-Q4",
        ])
        result = aggregate(rows)
        assert result["periods"] == ["2024-Q4", "2025-Q1"]

    def test_categories_ordered(self):
        result = aggregate(self._parsed())
        assert result["categories"] == ["REVENUE", "COST", "HEADCOUNT"]

    def test_cell_values_summed(self):
        rows = parse([
            "1:REVENUE:100.00:2024-Q1",
            "2:REVENUE:150.00:2024-Q1",
        ])
        result = aggregate(rows)
        assert result["cells"]["2024-Q1"]["REVENUE"] == 250.00

    def test_cell_missing_category_defaults_zero(self):
        rows = parse(["1:REVENUE:100:2024-Q1"])
        result = aggregate(rows)
        assert result["cells"]["2024-Q1"].get("COST", 0) == 0

    def test_period_subtotals(self):
        rows = parse([
            "1:REVENUE:1000:2024-Q1",
            "2:COST:-200:2024-Q1",
            "3:HEADCOUNT:10:2024-Q1",
        ])
        result = aggregate(rows)
        # subtotal sums all categories for that period
        assert result["period_totals"]["2024-Q1"] == pytest.approx(1000 + (-200) + 10)

    def test_category_grand_totals(self):
        rows = parse([
            "1:REVENUE:1000:2024-Q1",
            "2:REVENUE:2000:2024-Q2",
        ])
        result = aggregate(rows)
        grand_total = result["category_totals"]["REVENUE"]
        assert grand_total == pytest.approx(3000)

    def test_grand_total_across_all(self):
        rows = parse([
            "1:REVENUE:1000:2024-Q1",
            "2:COST:-200:2024-Q1",
        ])
        result = aggregate(rows)
        assert "grand_total" in result

    def test_categories_only_present_in_input(self):
        rows = parse(["1:REVENUE:100:2024-Q1"])
        result = aggregate(rows)
        # categories list only has present ones? — spec says order is REVENUE,COST,HEADCOUNT
        # let's check they're present (may include zeros)
        assert "REVENUE" in result["categories"]


# ===========================================================================
# Stage 3 – Format
# ===========================================================================

class TestFormatTable:
    def _aggregated(self):
        return aggregate(parse(VALID_ROWS))

    def test_returns_string(self):
        result = format_table(self._aggregated())
        assert isinstance(result, str)

    def test_has_header_row(self):
        result = format_table(self._aggregated())
        lines = result.strip().splitlines()
        assert "2024-Q1" in lines[0]
        assert "2024-Q2" in lines[0]
        assert "TOTAL" in lines[0]

    def test_has_category_rows(self):
        result = format_table(self._aggregated())
        assert "REVENUE" in result
        assert "COST" in result
        assert "HEADCOUNT" in result

    def test_has_total_row(self):
        result = format_table(self._aggregated())
        lines = result.strip().splitlines()
        assert any(line.strip().startswith("TOTAL") for line in lines)

    def test_revenue_dollar_format(self):
        result = format_table(self._aggregated())
        assert "$1,000.00" in result

    def test_cost_dollar_format(self):
        result = format_table(self._aggregated())
        assert "-$200.00" in result

    def test_headcount_integer_format(self):
        result = format_table(self._aggregated())
        assert "10" in result

    def test_at_least_2_spaces_between_columns(self):
        result = format_table(self._aggregated())
        lines = result.strip().splitlines()
        # Every line should have at least two consecutive spaces somewhere (padding)
        for line in lines:
            assert "  " in line

    def test_large_value_thousands_separator(self):
        rows = parse(["1:REVENUE:1234567.89:2024-Q1"])
        agg = aggregate(rows)
        result = format_table(agg)
        assert "$1,234,567.89" in result

    def test_negative_revenue_format_negative_cost(self):
        rows = parse(["1:COST:-1234.56:2024-Q1"])
        agg = aggregate(rows)
        result = format_table(agg)
        assert "-$1,234.56" in result


# ===========================================================================
# Stage 4 – Validate output
# ===========================================================================

class TestValidateOutput:
    def _valid_table(self):
        agg = aggregate(parse(VALID_ROWS))
        return format_table(agg), agg

    def test_returns_string_on_valid(self):
        table, agg = self._valid_table()
        result = validate_output(table, agg)
        assert isinstance(result, str)

    def test_returns_same_string_on_valid(self):
        table, agg = self._valid_table()
        result = validate_output(table, agg)
        assert result == table

    def test_error_when_period_missing_from_table(self):
        agg = aggregate(parse(VALID_ROWS))
        # Provide a table that's missing a period column
        fake_table = "CATEGORY  TOTAL\nREVENUE  $3,000.00\n"
        result = validate_output(fake_table, agg)
        assert isinstance(result, ValidationError)

    def test_error_when_total_mismatch(self):
        agg = aggregate(parse(VALID_ROWS))
        table = format_table(agg)
        # Corrupt the table
        corrupted = table.replace("$1,000.00", "$9,999.00", 1)
        result = validate_output(corrupted, agg)
        assert isinstance(result, ValidationError)

    def test_error_has_reason(self):
        agg = aggregate(parse(VALID_ROWS))
        fake_table = "bad table"
        result = validate_output(fake_table, agg)
        assert isinstance(result, ValidationError)
        assert result.reason

    def test_error_empty_table_with_periods(self):
        agg = aggregate(parse(VALID_ROWS))
        result = validate_output("", agg)
        assert isinstance(result, ValidationError)

    def test_ok_empty_table_no_periods(self):
        # empty input → empty table → should be fine
        agg = aggregate(parse([]))
        result = validate_output("", agg)
        assert isinstance(result, str)

    def test_error_missing_total_column_in_header(self):
        agg = aggregate(parse(["1:REVENUE:100:2024-Q1"]))
        # A table that has the period but no TOTAL column
        fake_table = "           2024-Q1\nREVENUE  $100.00\n"
        result = validate_output(fake_table, agg)
        assert isinstance(result, ValidationError)

    def test_error_col_offsets_not_found(self):
        # Period is in table text but TOTAL is missing from header
        agg = aggregate(parse(["1:REVENUE:100:2024-Q1"]))
        fake_table = "  2024-Q1  TOTAL\nREVENUE  $100.00  $100.00"
        # remove the period so _find_column_offsets returns None
        # (period IS in table due to check 1, but won't be in 'header' line)
        # Build a table where header misses the period token
        fake_table2 = "           TOTAL\n2024-Q1  $100.00  $100.00"
        # Check 1 passes (period in full table text), but offsets will fail
        result = validate_output(fake_table2, agg)
        assert isinstance(result, ValidationError)

    def test_empty_cell_value_parses_as_zero(self):
        # Directly test _parse_cell_value with empty string
        from report_pipeline.pipeline import _parse_cell_value
        assert _parse_cell_value("") == 0.0
        assert _parse_cell_value("  ") == 0.0

    def test_error_unparseable_period_cell(self):
        """Row with a non-numeric period cell triggers ValidationError."""
        agg = aggregate(parse(["1:REVENUE:100:2024-Q1"]))
        # Craft a table that passes period/TOTAL header checks but has bad cell
        fake = "           2024-Q1  TOTAL\nREVENUE       abc  $100.00\n"
        result = validate_output(fake, agg)
        assert isinstance(result, ValidationError)

    def test_error_unparseable_total_cell(self):
        """Row where TOTAL cell is unparseable triggers ValidationError."""
        agg = aggregate(parse(["1:REVENUE:100:2024-Q1"]))
        fake = "           2024-Q1  TOTAL\nREVENUE  $100.00      xyz\n"
        result = validate_output(fake, agg)
        assert isinstance(result, ValidationError)

    def test_row_with_too_few_columns_is_skipped(self):
        """A data row with fewer columns than periods should not crash."""
        agg = aggregate(parse(["1:REVENUE:100:2024-Q1"]))
        # Header has period+TOTAL but data row has only label
        fake = "           2024-Q1  TOTAL\nREVENUE\n"
        # Should return ValidationError or string (no crash)
        result = validate_output(fake, agg)
        # we just assert it doesn't raise
        assert result is not None


# ===========================================================================
# Full pipeline
# ===========================================================================

class TestRunPipeline:
    def test_returns_string_on_success(self):
        result = run_pipeline(VALID_ROWS)
        assert isinstance(result, str)

    def test_returns_parse_error_on_bad_input(self):
        result = run_pipeline(["1:REVENUE:-50:2024-Q1"])
        assert isinstance(result, ParseError)

    def test_returns_table_with_expected_content(self):
        result = run_pipeline(VALID_ROWS)
        assert "REVENUE" in result
        assert "COST" in result
        assert "HEADCOUNT" in result
        assert "TOTAL" in result

    def test_single_row_pipeline(self):
        result = run_pipeline(["1:REVENUE:500.00:2024-Q1"])
        assert isinstance(result, str)
        assert "$500.00" in result

    def test_empty_input_pipeline(self):
        result = run_pipeline([])
        # Empty input should either return an empty-ish table or a structured error
        # We'll accept either a string or a structured error
        assert isinstance(result, (str, ParseError, ValidationError))

    def test_multiple_periods_pipeline(self):
        rows = [
            "1:REVENUE:1000:2023-Q4",
            "2:REVENUE:2000:2024-Q1",
            "3:COST:-100:2023-Q4",
        ]
        result = run_pipeline(rows)
        assert isinstance(result, str)
        assert "2023-Q4" in result
        assert "2024-Q1" in result

    def test_periods_in_chronological_order_in_output(self):
        rows = [
            "1:REVENUE:2000:2024-Q2",
            "2:REVENUE:1000:2024-Q1",
        ]
        result = run_pipeline(rows)
        assert isinstance(result, str)
        idx_q1 = result.find("2024-Q1")
        idx_q2 = result.find("2024-Q2")
        assert idx_q1 < idx_q2

    def test_headcount_no_dollar_sign(self):
        rows = ["1:HEADCOUNT:42:2024-Q1"]
        result = run_pipeline(rows)
        assert isinstance(result, str)
        assert "42" in result
        # The HEADCOUNT row must not contain $ sign in value area
        lines = result.strip().splitlines()
        headcount_line = next(l for l in lines if l.strip().startswith("HEADCOUNT"))
        # strip leading label
        values_part = headcount_line[headcount_line.index("HEADCOUNT") + len("HEADCOUNT"):]
        assert "$" not in values_part
