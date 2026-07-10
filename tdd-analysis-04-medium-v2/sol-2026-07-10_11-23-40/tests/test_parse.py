"""Tests for the parse stage."""
from decimal import Decimal

import pytest

from report_pipeline import ParsedRow, ParseError, parse


# ---------------------------------------------------------------------------
# Error tests
# ---------------------------------------------------------------------------

def test_parse_error_wrong_field_count():
    bad = "1:REVENUE:2024-Q1"  # only 3 fields
    result = parse([bad])
    assert isinstance(result, ParseError)
    assert result.stage == "parse"
    assert result.raw_input == bad
    assert "4" in result.reason  # mentions expected field count


def test_parse_error_negative_revenue():
    bad = "1:REVENUE:-100.00:2024-Q1"
    result = parse([bad])
    assert isinstance(result, ParseError)
    assert "REVENUE" in result.reason or "negative" in result.reason.lower()


def test_parse_error_negative_headcount():
    bad = "1:HEADCOUNT:-5:2024-Q1"
    result = parse([bad])
    assert isinstance(result, ParseError)
    assert isinstance(result, ParseError)


def test_parse_error_unknown_category():
    bad = "1:EXPENSES:100.00:2024-Q1"
    result = parse([bad])
    assert isinstance(result, ParseError)
    assert "EXPENSES" in result.reason or "category" in result.reason.lower()


def test_parse_error_invalid_period_quarter():
    bad = "1:REVENUE:100.00:2024-Q5"
    result = parse([bad])
    assert isinstance(result, ParseError)
    assert "PERIOD" in result.reason or "period" in result.reason.lower()


def test_parse_error_invalid_period_format():
    bad = "1:REVENUE:100.00:2024-01"
    result = parse([bad])
    assert isinstance(result, ParseError)


def test_parse_error_invalid_row_id():
    bad = "abc:REVENUE:100.00:2024-Q1"
    result = parse([bad])
    assert isinstance(result, ParseError)
    assert "ROW_ID" in result.reason


def test_parse_error_zero_row_id():
    bad = "0:REVENUE:100.00:2024-Q1"
    result = parse([bad])
    assert isinstance(result, ParseError)


def test_parse_error_invalid_value():
    bad = "1:REVENUE:not_a_number:2024-Q1"
    result = parse([bad])
    assert isinstance(result, ParseError)
    assert "VALUE" in result.reason or "decimal" in result.reason.lower()


def test_parse_error_identifies_failing_row():
    """When one of several rows fails, the error identifies that row."""
    result = parse([
        "1:REVENUE:100.00:2024-Q1",
        "2:BADCAT:50.00:2024-Q1",
    ])
    assert isinstance(result, ParseError)
    assert result.raw_input == "2:BADCAT:50.00:2024-Q1"


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

def test_parse_multiple_rows_all_categories():
    result = parse([
        "1:REVENUE:500.00:2024-Q1",
        "2:COST:-200.00:2024-Q1",
        "3:HEADCOUNT:10:2024-Q1",
    ])
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0] == ParsedRow(1, "REVENUE", Decimal("500.00"), "2024-Q1")
    assert result[1] == ParsedRow(2, "COST", Decimal("-200.00"), "2024-Q1")
    assert result[2] == ParsedRow(3, "HEADCOUNT", Decimal("10"), "2024-Q1")


def test_parse_empty_input_returns_empty_list():
    result = parse([])
    assert result == []


def test_parse_cost_negative_value_is_valid():
    result = parse(["1:COST:-999.99:2023-Q4"])
    assert isinstance(result, list)
    assert result[0].value == Decimal("-999.99")


def test_parse_single_revenue_row():
    result = parse(["1:REVENUE:1000.00:2024-Q1"])
    assert isinstance(result, list)
    assert len(result) == 1
    row = result[0]
    assert isinstance(row, ParsedRow)
    assert row.row_id == 1
    assert row.category == "REVENUE"
    assert row.value == Decimal("1000.00")
    assert row.period == "2024-Q1"
