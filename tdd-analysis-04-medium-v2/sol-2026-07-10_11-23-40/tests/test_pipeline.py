"""Tests for the full run_pipeline function."""
import pytest
from report_pipeline import ParseError, ValidationError, run_pipeline


def test_run_pipeline_returns_string_on_success():
    raw = [
        "1:REVENUE:1000.00:2024-Q1",
        "2:COST:-200.00:2024-Q1",
        "3:HEADCOUNT:10:2024-Q1",
    ]
    result = run_pipeline(raw)
    assert isinstance(result, str)
    assert "REVENUE" in result
    assert "COST" in result
    assert "HEADCOUNT" in result
    assert "2024-Q1" in result
    assert "TOTAL" in result


def test_run_pipeline_parse_error_propagates():
    raw = ["1:BADCAT:100.00:2024-Q1"]
    result = run_pipeline(raw)
    assert isinstance(result, ParseError)
    assert result.stage == "parse"


def test_run_pipeline_multiple_periods():
    raw = [
        "1:REVENUE:1000.00:2024-Q1",
        "2:REVENUE:2000.00:2024-Q2",
    ]
    result = run_pipeline(raw)
    assert isinstance(result, str)
    assert "2024-Q1" in result
    assert "2024-Q2" in result
    assert "$1,000.00" in result
    assert "$2,000.00" in result


def test_run_pipeline_correct_revenue_total():
    raw = [
        "1:REVENUE:1000.00:2024-Q1",
        "2:REVENUE:2000.00:2024-Q2",
    ]
    result = run_pipeline(raw)
    assert isinstance(result, str)
    assert "$3,000.00" in result  # category total
