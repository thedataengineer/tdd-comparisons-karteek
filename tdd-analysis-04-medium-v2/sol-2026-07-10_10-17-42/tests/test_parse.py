"""Tests for the parse stage."""

from decimal import Decimal
import pytest

from report_pipeline.models import ParsedRow, ParseError
from report_pipeline.parse import parse


# ---------------------------------------------------------------------------
# Happy-path parsing
# ---------------------------------------------------------------------------

def test_parse_single_valid_revenue_row():
    result = parse(["1:REVENUE:1000.00:2024-Q1"])
    assert len(result) == 1
    row = result[0]
    assert isinstance(row, ParsedRow)
    assert row.row_id == 1
    assert row.category == "REVENUE"
    assert row.value == Decimal("1000.00")
    assert row.period == "2024-Q1"


def test_parse_multiple_valid_rows():
    rows = [
        "1:REVENUE:500.00:2024-Q1",
        "2:COST:-200.00:2024-Q1",
        "3:HEADCOUNT:10:2024-Q1",
    ]
    result = parse(rows)
    assert len(result) == 3
    assert result[0].row_id == 1
    assert result[1].category == "COST"
    assert result[1].value == Decimal("-200.00")
    assert result[2].value == Decimal("10")


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_parse_error_too_few_fields():
    result = parse(["1:REVENUE:100"])
    assert isinstance(result, ParseError)
    assert result.input_string == "1:REVENUE:100"
    assert "4" in result.reason  # mentions expected count


def test_parse_error_invalid_category():
    result = parse(["1:PROFIT:100.00:2024-Q1"])
    assert isinstance(result, ParseError)
    assert "PROFIT" in result.reason


def test_parse_error_non_numeric_value():
    result = parse(["1:REVENUE:abc:2024-Q1"])
    assert isinstance(result, ParseError)
    assert "abc" in result.reason


def test_parse_error_negative_revenue():
    result = parse(["1:REVENUE:-500.00:2024-Q1"])
    assert isinstance(result, ParseError)
    assert "REVENUE" in result.reason


def test_parse_error_negative_headcount():
    result = parse(["1:HEADCOUNT:-5:2024-Q1"])
    assert isinstance(result, ParseError)
    assert "HEADCOUNT" in result.reason


def test_parse_error_invalid_period_format():
    result = parse(["1:REVENUE:100.00:2024-Q5"])
    assert isinstance(result, ParseError)
    assert "2024-Q5" in result.reason


def test_parse_error_invalid_period_not_quarter():
    result = parse(["1:REVENUE:100.00:2024-M1"])
    assert isinstance(result, ParseError)
    assert "2024-M1" in result.reason


def test_parse_error_identifies_failing_input_string():
    """The first bad row is reported; subsequent rows are not parsed."""
    rows = [
        "1:REVENUE:100.00:2024-Q1",
        "2:BAD:50.00:2024-Q1",
        "3:COST:-10.00:2024-Q1",
    ]
    result = parse(rows)
    assert isinstance(result, ParseError)
    assert result.input_string == "2:BAD:50.00:2024-Q1"


def test_parse_empty_input_returns_empty_list():
    result = parse([])
    assert result == []


def test_parse_error_zero_row_id():
    result = parse(["0:REVENUE:100.00:2024-Q1"])
    assert isinstance(result, ParseError)
    assert "ROW_ID" in result.reason


def test_parse_error_non_integer_row_id():
    result = parse(["abc:REVENUE:100.00:2024-Q1"])
    assert isinstance(result, ParseError)
    assert "ROW_ID" in result.reason


def test_parse_error_period_too_short():
    """Period shorter than 7 chars should fail."""
    result = parse(["1:REVENUE:100.00:24-Q1"])
    assert isinstance(result, ParseError)
    assert "24-Q1" in result.reason


def test_parse_error_period_non_digit_year():
    """Period with non-digit year should fail."""
    result = parse(["1:REVENUE:100.00:ABCD-Q1"])
    assert isinstance(result, ParseError)
    assert "ABCD-Q1" in result.reason


def test_parse_cost_positive_value_is_valid():
    """COST may also be positive (spec only forbids negative REVENUE/HEADCOUNT)."""
    result = parse(["1:COST:50.00:2024-Q1"])
    assert isinstance(result, list)
    assert result[0].value == Decimal("50.00")


def test_parse_decimal_value_precision_preserved():
    """Decimal precision should be preserved exactly."""
    result = parse(["1:REVENUE:12345.67:2024-Q1"])
    assert isinstance(result, list)
    assert result[0].value == Decimal("12345.67")
