"""Tests for the parse stage."""

import pytest
from decimal import Decimal

from report_pipeline.parse import parse, ParsedRow, ParseError


# ---------- Happy-path tests ----------

def test_parse_single_revenue_row():
    result = parse(["1:REVENUE:1000.00:2024-Q1"])
    assert isinstance(result, list)
    assert len(result) == 1
    row = result[0]
    assert row.row_id == 1
    assert row.category == "REVENUE"
    assert row.value == Decimal("1000.00")
    assert row.period == "2024-Q1"


def test_parse_single_cost_row():
    result = parse(["2:COST:-500.00:2024-Q2"])
    assert isinstance(result, list)
    assert result[0].value == Decimal("-500.00")
    assert result[0].category == "COST"


def test_parse_headcount_row():
    result = parse(["3:HEADCOUNT:42:2024-Q3"])
    assert isinstance(result, list)
    assert result[0].value == Decimal("42")
    assert result[0].category == "HEADCOUNT"


def test_parse_multiple_rows():
    lines = [
        "1:REVENUE:1000.00:2024-Q1",
        "2:COST:-200.00:2024-Q1",
        "3:HEADCOUNT:10:2024-Q1",
    ]
    result = parse(lines)
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0].row_id == 1
    assert result[1].row_id == 2
    assert result[2].row_id == 3


def test_parse_empty_input():
    result = parse([])
    assert result == []


def test_parse_all_quarters():
    for q in range(1, 5):
        result = parse([f"1:REVENUE:100:2024-Q{q}"])
        assert isinstance(result, list)
        assert result[0].period == f"2024-Q{q}"


def test_parse_positive_cost():
    result = parse(["1:COST:300.00:2023-Q4"])
    assert isinstance(result, list)
    assert result[0].value == Decimal("300.00")


# ---------- Error cases ----------

def test_parse_wrong_field_count():
    err = parse(["1:REVENUE:100"])
    assert isinstance(err, ParseError)
    assert "4" in err.reason or "fields" in err.reason


def test_parse_too_many_fields():
    err = parse(["1:REVENUE:100:2024-Q1:extra"])
    assert isinstance(err, ParseError)


def test_parse_invalid_row_id_not_int():
    err = parse(["abc:REVENUE:100:2024-Q1"])
    assert isinstance(err, ParseError)
    assert "ROW_ID" in err.reason


def test_parse_invalid_row_id_zero():
    err = parse(["0:REVENUE:100:2024-Q1"])
    assert isinstance(err, ParseError)
    assert "positive" in err.reason


def test_parse_invalid_row_id_negative():
    err = parse(["-1:REVENUE:100:2024-Q1"])
    assert isinstance(err, ParseError)
    assert "positive" in err.reason


def test_parse_duplicate_row_id():
    err = parse([
        "1:REVENUE:100:2024-Q1",
        "1:COST:-50:2024-Q1",
    ])
    assert isinstance(err, ParseError)
    assert "duplicate" in err.reason.lower()


def test_parse_unknown_category():
    err = parse(["1:PROFIT:100:2024-Q1"])
    assert isinstance(err, ParseError)
    assert "CATEGORY" in err.reason


def test_parse_invalid_value_not_decimal():
    err = parse(["1:REVENUE:abc:2024-Q1"])
    assert isinstance(err, ParseError)
    assert "VALUE" in err.reason


def test_parse_negative_revenue():
    err = parse(["1:REVENUE:-100:2024-Q1"])
    assert isinstance(err, ParseError)
    assert "REVENUE" in err.reason
    assert "negative" in err.reason.lower()


def test_parse_negative_headcount():
    err = parse(["1:HEADCOUNT:-5:2024-Q1"])
    assert isinstance(err, ParseError)
    assert "HEADCOUNT" in err.reason
    assert "negative" in err.reason.lower()


def test_parse_invalid_period_format():
    err = parse(["1:REVENUE:100:2024-Q5"])
    assert isinstance(err, ParseError)
    assert "PERIOD" in err.reason


def test_parse_invalid_period_missing_q():
    err = parse(["1:REVENUE:100:2024-1"])
    assert isinstance(err, ParseError)


def test_parse_invalid_period_wrong_format():
    err = parse(["1:REVENUE:100:Q1-2024"])
    assert isinstance(err, ParseError)


def test_parse_error_includes_raw():
    raw = "bad_line"
    err = parse([raw])
    assert isinstance(err, ParseError)
    assert err.raw == raw


def test_parse_first_error_returned():
    """Only the first failing line produces an error."""
    lines = [
        "1:REVENUE:100:2024-Q1",   # OK
        "2:BADCAT:100:2024-Q1",    # error
        "3:REVENUE:100:2024-Q1",   # also OK, but won't be reached
    ]
    err = parse(lines)
    assert isinstance(err, ParseError)
    assert err.raw == "2:BADCAT:100:2024-Q1"
