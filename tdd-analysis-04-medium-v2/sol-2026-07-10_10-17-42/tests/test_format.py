"""Tests for the format stage."""

from decimal import Decimal
import pytest

from report_pipeline.models import AggregatedData, FormatError
from report_pipeline.format_stage import format_table
from report_pipeline.aggregate import aggregate
from report_pipeline.parse import parse


def make_aggregated(raw_rows):
    """Helper: parse → aggregate."""
    parsed = parse(raw_rows)
    assert not isinstance(parsed, FormatError)
    return aggregate(parsed)


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------

def test_format_table_returns_string():
    agg = make_aggregated(["1:REVENUE:1000.00:2024-Q1"])
    result = format_table(agg)
    assert isinstance(result, str)


def test_format_table_contains_period_header():
    agg = make_aggregated(["1:REVENUE:1000.00:2024-Q1"])
    result = format_table(agg)
    assert "2024-Q1" in result


def test_format_table_contains_total_header():
    agg = make_aggregated(["1:REVENUE:1000.00:2024-Q1"])
    result = format_table(agg)
    assert "TOTAL" in result


def test_format_table_contains_category_rows():
    rows = [
        "1:REVENUE:1000.00:2024-Q1",
        "2:COST:-200.00:2024-Q1",
        "3:HEADCOUNT:5:2024-Q1",
    ]
    agg = make_aggregated(rows)
    result = format_table(agg)
    assert isinstance(result, str)
    assert "REVENUE" in result
    assert "COST" in result
    assert "HEADCOUNT" in result


# ---------------------------------------------------------------------------
# Value formatting
# ---------------------------------------------------------------------------

def test_format_revenue_uses_dollar_thousands_two_decimals():
    agg = make_aggregated(["1:REVENUE:1234.56:2024-Q1"])
    result = format_table(agg)
    assert "$1,234.56" in result


def test_format_revenue_large_value():
    agg = make_aggregated(["1:REVENUE:1000000.00:2024-Q1"])
    result = format_table(agg)
    assert "$1,000,000.00" in result


def test_format_negative_cost_has_minus_outside_dollar():
    agg = make_aggregated(["1:COST:-200.00:2024-Q1"])
    result = format_table(agg)
    assert "-$200.00" in result


def test_format_headcount_is_plain_integer():
    agg = make_aggregated(["1:HEADCOUNT:42:2024-Q1"])
    result = format_table(agg)
    assert isinstance(result, str)
    lines = result.splitlines()
    # Find the HEADCOUNT row
    hc_line = next(l for l in lines if l.startswith("HEADCOUNT"))
    # Should contain plain integer, not $42.00
    assert "42" in hc_line
    assert "$" not in hc_line


# ---------------------------------------------------------------------------
# Layout / alignment
# ---------------------------------------------------------------------------

def test_format_values_right_aligned():
    """Each period column value should be right-aligned (right edge lines up)."""
    rows = [
        "1:REVENUE:1234.56:2024-Q1",
        "2:COST:-9.00:2024-Q1",
    ]
    agg = make_aggregated(rows)
    result = format_table(agg)
    lines = result.splitlines()
    # Header line and data lines should share the same right edge for the period col
    # The simplest check: each data line has the same length (all padded to same width)
    # Actually, columns are right-justified within their widths; check at least
    # that the REVENUE and COST values are right-aligned in the same column.
    # We locate the end of the "2024-Q1" header token and check values end there too.
    header = lines[0]
    # Find index where "2024-Q1" ends in header
    idx = header.index("2024-Q1") + len("2024-Q1")
    # In each data row, the chars up to idx should end with the right-justified value
    revenue_line = next(l for l in lines if l.startswith("REVENUE"))
    cost_line = next(l for l in lines if l.startswith("COST"))
    # Both values should end at the same column position as the header
    assert revenue_line[idx - len("$1,234.56"):idx] == "$1,234.56"
    assert cost_line[idx - len("-$9.00"):idx] == "-$9.00"


def test_format_total_row_sums_period_columns():
    """The TOTAL row value for a period should equal sum of all categories in that period."""
    rows = [
        "1:REVENUE:1000.00:2024-Q1",
        "2:COST:-200.00:2024-Q1",
    ]
    agg = make_aggregated(rows)
    result = format_table(agg)
    assert isinstance(result, str)
    lines = result.splitlines()
    total_line = next(l for l in lines if l.startswith("TOTAL"))
    # 1000 + (-200) = 800
    assert "$800.00" in total_line


def test_format_periods_chronological_in_header():
    rows = [
        "1:REVENUE:100.00:2024-Q3",
        "2:REVENUE:200.00:2023-Q2",
    ]
    agg = make_aggregated(rows)
    result = format_table(agg)
    header = result.splitlines()[0]
    pos_q2 = header.index("2023-Q2")
    pos_q3 = header.index("2024-Q3")
    assert pos_q2 < pos_q3, "2023-Q2 should appear before 2024-Q3 in header"


def test_format_total_column_per_category():
    rows = [
        "1:REVENUE:1000.00:2024-Q1",
        "2:REVENUE:500.00:2024-Q2",
    ]
    agg = make_aggregated(rows)
    result = format_table(agg)
    revenue_line = next(l for l in result.splitlines() if l.startswith("REVENUE"))
    # Total for REVENUE across both periods = 1500
    assert "$1,500.00" in revenue_line


# ---------------------------------------------------------------------------
# Format propagates validation errors
# ---------------------------------------------------------------------------

def test_format_table_returns_format_error_when_validation_fails(monkeypatch):
    """If validate_output returns a FormatError, format_table propagates it."""
    from report_pipeline import format_stage as fs_module
    from report_pipeline.models import FormatError

    def fake_validate(table, agg):
        return FormatError(reason="injected validation error")

    monkeypatch.setattr(fs_module, "validate_output", fake_validate)
    agg = make_aggregated(["1:REVENUE:1000.00:2024-Q1"])
    result = format_table(agg)
    assert isinstance(result, FormatError)
    assert result.reason == "injected validation error"
