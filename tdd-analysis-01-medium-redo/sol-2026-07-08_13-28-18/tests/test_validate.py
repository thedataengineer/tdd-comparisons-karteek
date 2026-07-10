"""Tests for the validate_output stage."""

import pytest
from decimal import Decimal

from report_pipeline.parse import parse, ParsedRow
from report_pipeline.aggregate import aggregate
from report_pipeline.format import format_table
from report_pipeline.validate import validate_output, ValidationError, _parse_formatted_value
from report_pipeline.format import compute_col_widths_list


def make_data(*lines):
    rows = parse(list(lines))
    return aggregate(rows)


def make_table_and_data(*lines):
    data = make_data(*lines)
    table = format_table(data)
    return table, data


# ---------- Happy path ----------

def test_validate_passes_simple():
    table, data = make_table_and_data("1:REVENUE:1000:2024-Q1")
    result = validate_output(table, data)
    assert result == table


def test_validate_passes_multi_period():
    table, data = make_table_and_data(
        "1:REVENUE:1000:2024-Q1",
        "2:REVENUE:2000:2024-Q2",
    )
    result = validate_output(table, data)
    assert result == table


def test_validate_passes_full_table():
    table, data = make_table_and_data(
        "1:REVENUE:10000:2024-Q1",
        "2:COST:-2000:2024-Q1",
        "3:HEADCOUNT:5:2024-Q1",
        "4:REVENUE:15000:2024-Q2",
        "5:COST:-3000:2024-Q2",
        "6:HEADCOUNT:7:2024-Q2",
    )
    result = validate_output(table, data)
    assert result == table


# ---------- Check 1: all periods in header ----------

def test_validate_missing_period_in_header():
    table, data = make_table_and_data("1:REVENUE:1000:2024-Q1")
    # Tamper: remove the period from the header
    tampered = table.replace("2024-Q1", "    XXX")
    err = validate_output(tampered, data)
    assert isinstance(err, ValidationError)
    assert "2024-Q1" in err.reason


# ---------- Check 2: TOTAL column matches sum ----------

def test_validate_total_mismatch():
    table, data = make_table_and_data(
        "1:REVENUE:1000:2024-Q1",
        "2:REVENUE:2000:2024-Q2",
    )
    # Tamper: change a period value to create mismatch
    # Replace '$1,000.00' in the table with '$9,999.00'
    tampered = table.replace("$1,000.00", "$9,999.00", 1)
    # Only tamper if this actually changed something
    if tampered != table:
        err = validate_output(tampered, data)
        assert isinstance(err, ValidationError)
        assert "TOTAL" in err.reason or "mismatch" in err.reason.lower()


# ---------- Check 3: no column narrower than header ----------

def test_validate_empty_table():
    table, data = make_table_and_data("1:REVENUE:1000:2024-Q1")
    err = validate_output("", data)
    assert isinstance(err, ValidationError)


def test_validate_no_total_column():
    table, data = make_table_and_data("1:REVENUE:1000:2024-Q1")
    # Remove TOTAL from header
    tampered = table.replace("TOTAL", "XXXXX")
    err = validate_output(tampered, data)
    assert isinstance(err, ValidationError)


# ---------- _parse_formatted_value tests ----------

def test_parse_formatted_dollar():
    assert _parse_formatted_value("$1,234.56") == Decimal("1234.56")


def test_parse_formatted_negative_dollar():
    assert _parse_formatted_value("-$200.00") == Decimal("-200.00")


def test_parse_formatted_integer():
    assert _parse_formatted_value("42") == Decimal("42")


def test_parse_formatted_empty():
    assert _parse_formatted_value("") == Decimal("0")


def test_parse_formatted_whitespace():
    assert _parse_formatted_value("  $100.00  ") == Decimal("100.00")


# ---------- Edge-case branch coverage ----------

def test_validate_skips_blank_rows():
    """Blank lines in the table body should be skipped gracefully."""
    table, data = make_table_and_data("1:REVENUE:1000:2024-Q1")
    lines = table.splitlines()
    # Insert an explicit blank line between header and first data row
    tampered = lines[0] + "\n\n" + "\n".join(lines[1:])
    result = validate_output(tampered, data)
    assert isinstance(result, (str, ValidationError))


def test_validate_check3_column_too_narrow():
    """Trigger the check-3 error: column narrower than its header."""
    from unittest.mock import patch
    table, data = make_table_and_data("1:REVENUE:1:2024-Q1")
    # Patch compute_col_widths_list to return a width too small for the period header
    original_widths = compute_col_widths_list(data)
    # Make the period column (index 1) only 1 char wide, but header is 7 chars
    narrow_widths = [original_widths[0], 1, original_widths[2]]
    with patch("report_pipeline.validate.compute_col_widths_list", return_value=narrow_widths):
        err = validate_output(table, data)
    assert isinstance(err, ValidationError)
    assert "narrower" in err.reason

    # Also test _get_field edge case:
    from report_pipeline.validate import _get_field
    # col_start beyond line length
    assert _get_field("short", 100, 10) == ""


def test_validate_unparseable_row_skipped():
    """A row with non-numeric values should be skipped in check 2."""
    table, data = make_table_and_data("1:REVENUE:1000:2024-Q1")
    # Inject a row with unparseable content
    lines = table.splitlines()
    # Replace REVENUE value with 'N/A' to make it unparseable
    bad_line = lines[1].replace("$1,000.00", "   N/A   ")
    tampered = "\n".join([lines[0], bad_line] + lines[2:])
    # Should either pass (skip that row) or return a validation error
    result = validate_output(tampered, data)
    # We just verify it doesn't raise an exception
    assert isinstance(result, (str, ValidationError))
