"""Tests for the parse stage."""

import pytest
from report_pipeline.parse import parse, ParsedRow, ParseError


# ── Happy-path tests ──────────────────────────────────────────────────────────

def test_parse_single_revenue_row():
    result = parse(["1:REVENUE:1000.00:2024-Q1"])
    assert isinstance(result, list)
    assert len(result) == 1
    row = result[0]
    assert isinstance(row, ParsedRow)
    assert row.row_id == 1
    assert row.category == "REVENUE"
    assert row.value == 1000.00
    assert row.period == "2024-Q1"


def test_parse_multiple_rows():
    raw = [
        "1:REVENUE:500.00:2024-Q1",
        "2:COST:-200.00:2024-Q1",
        "3:HEADCOUNT:10:2024-Q1",
    ]
    result = parse(raw)
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0].category == "REVENUE"
    assert result[1].category == "COST"
    assert result[2].category == "HEADCOUNT"


def test_parse_negative_cost_is_valid():
    result = parse(["1:COST:-999.99:2023-Q4"])
    assert isinstance(result, list)
    assert result[0].value == pytest.approx(-999.99)


def test_parse_zero_value():
    result = parse(["1:COST:0.00:2023-Q1"])
    assert isinstance(result, list)
    assert result[0].value == 0.0


def test_parse_integer_value():
    result = parse(["1:HEADCOUNT:15:2024-Q2"])
    assert isinstance(result, list)
    assert result[0].value == 15.0


def test_parse_all_quarters():
    raw = [f"{i}:REVENUE:100:2024-Q{i}" for i in range(1, 5)]
    result = parse(raw)
    assert isinstance(result, list)
    assert len(result) == 4


def test_parse_returns_error_type_with_stage():
    err = parse(["bad-input"])
    assert isinstance(err, ParseError)
    assert err.stage == "parse"


def test_parse_empty_input():
    result = parse([])
    assert result == []


# ── Wrong field count ─────────────────────────────────────────────────────────

def test_parse_too_few_fields():
    err = parse(["1:REVENUE:100"])
    assert isinstance(err, ParseError)
    assert "4" in err.reason


def test_parse_too_many_fields():
    err = parse(["1:REVENUE:100:2024-Q1:EXTRA"])
    assert isinstance(err, ParseError)
    assert "4" in err.reason


# ── ROW_ID validation ─────────────────────────────────────────────────────────

def test_parse_non_integer_row_id():
    err = parse(["abc:REVENUE:100:2024-Q1"])
    assert isinstance(err, ParseError)
    assert "ROW_ID" in err.reason


def test_parse_zero_row_id():
    err = parse(["0:REVENUE:100:2024-Q1"])
    assert isinstance(err, ParseError)
    assert "positive" in err.reason.lower()


def test_parse_negative_row_id():
    err = parse(["-1:REVENUE:100:2024-Q1"])
    assert isinstance(err, ParseError)
    assert "positive" in err.reason.lower()


def test_parse_duplicate_row_id():
    err = parse(["1:REVENUE:100:2024-Q1", "1:COST:-50:2024-Q1"])
    assert isinstance(err, ParseError)
    assert "Duplicate" in err.reason


def test_parse_float_row_id():
    err = parse(["1.5:REVENUE:100:2024-Q1"])
    assert isinstance(err, ParseError)
    assert "ROW_ID" in err.reason


# ── CATEGORY validation ───────────────────────────────────────────────────────

def test_parse_invalid_category():
    err = parse(["1:EXPENSES:100:2024-Q1"])
    assert isinstance(err, ParseError)
    assert "CATEGORY" in err.reason


def test_parse_lowercase_category():
    err = parse(["1:revenue:100:2024-Q1"])
    assert isinstance(err, ParseError)
    assert "CATEGORY" in err.reason


# ── VALUE validation ──────────────────────────────────────────────────────────

def test_parse_non_numeric_value():
    err = parse(["1:REVENUE:abc:2024-Q1"])
    assert isinstance(err, ParseError)
    assert "VALUE" in err.reason


def test_parse_negative_revenue():
    err = parse(["1:REVENUE:-100:2024-Q1"])
    assert isinstance(err, ParseError)
    assert "Negative" in err.reason


def test_parse_negative_headcount():
    err = parse(["1:HEADCOUNT:-5:2024-Q1"])
    assert isinstance(err, ParseError)
    assert "Negative" in err.reason


# ── PERIOD validation ─────────────────────────────────────────────────────────

def test_parse_invalid_period_format():
    err = parse(["1:REVENUE:100:2024Q1"])
    assert isinstance(err, ParseError)
    assert "PERIOD" in err.reason


def test_parse_period_q0():
    err = parse(["1:REVENUE:100:2024-Q0"])
    assert isinstance(err, ParseError)
    assert "PERIOD" in err.reason


def test_parse_period_q5():
    err = parse(["1:REVENUE:100:2024-Q5"])
    assert isinstance(err, ParseError)
    assert "PERIOD" in err.reason


def test_parse_period_wrong_separator():
    err = parse(["1:REVENUE:100:2024/Q1"])
    assert isinstance(err, ParseError)
    assert "PERIOD" in err.reason


# ── Error contains the offending raw string ───────────────────────────────────

def test_parse_error_includes_raw_string():
    bad = "1:REVENUE:-5:2024-Q1"
    err = parse([bad])
    assert isinstance(err, ParseError)
    assert err.raw == bad


def test_parse_first_bad_row_reported():
    """Only the first failing string is reported."""
    raw = ["1:REVENUE:100:2024-Q1", "bad", "3:COST:-10:2024-Q1"]
    err = parse(raw)
    assert isinstance(err, ParseError)
    assert err.raw == "bad"
