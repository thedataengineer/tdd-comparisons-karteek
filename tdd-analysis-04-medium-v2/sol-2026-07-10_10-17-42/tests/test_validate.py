"""Tests for the validate_output stage."""

from decimal import Decimal
import pytest

from report_pipeline.models import AggregatedData, FormatError
from report_pipeline.validate_stage import validate_output
from report_pipeline.aggregate import aggregate
from report_pipeline.parse import parse
from report_pipeline.format_stage import format_table


def make_agg(raw_rows):
    parsed = parse(raw_rows)
    return aggregate(parsed)


def test_validate_returns_none_for_valid_table():
    agg = make_agg(["1:REVENUE:1000.00:2024-Q1"])
    table = format_table(agg)
    assert isinstance(table, str)
    result = validate_output(table, agg)
    assert result is None


def test_validate_error_when_period_missing_from_header():
    agg = make_agg(["1:REVENUE:1000.00:2024-Q1"])
    # Tamper with the table: remove the period from the header
    table = format_table(agg)
    assert isinstance(table, str)
    tampered = table.replace("2024-Q1", "XXXXXXX")
    result = validate_output(tampered, agg)
    assert isinstance(result, FormatError)
    assert "2024-Q1" in result.reason


def test_validate_error_when_total_column_missing():
    agg = make_agg(["1:REVENUE:1000.00:2024-Q1"])
    table = format_table(agg)
    assert isinstance(table, str)
    tampered = table.replace("TOTAL", "XXXXX")
    result = validate_output(tampered, agg)
    assert isinstance(result, FormatError)
    assert "TOTAL" in result.reason


def test_validate_error_for_empty_table():
    """An empty string is not a valid table."""
    agg = make_agg(["1:REVENUE:1000.00:2024-Q1"])
    result = validate_output("", agg)
    assert isinstance(result, FormatError)
    assert "empty" in result.reason


def test_validate_checks_total_column_arithmetic():
    """validate_output should detect when TOTAL column doesn't match period sums."""
    agg = make_agg([
        "1:REVENUE:1000.00:2024-Q1",
        "2:REVENUE:500.00:2024-Q2",
    ])
    # Force a wrong total into the table
    table = format_table(agg)
    assert isinstance(table, str)
    # Replace the correct TOTAL for REVENUE ($1,500.00) with a wrong value
    tampered = table.replace("$1,500.00", "$9,999.00")
    result = validate_output(tampered, agg)
    assert isinstance(result, FormatError)
    assert "TOTAL" in result.reason.upper() or "mismatch" in result.reason.lower()
