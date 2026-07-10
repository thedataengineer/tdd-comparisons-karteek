"""Tests for the full pipeline."""

import pytest
from decimal import Decimal

from report_pipeline.pipeline import run_pipeline
from report_pipeline.parse import ParseError
from report_pipeline.validate import ValidationError


SAMPLE_LINES = [
    "1:REVENUE:10000.00:2024-Q1",
    "2:COST:-2000.00:2024-Q1",
    "3:HEADCOUNT:5:2024-Q1",
    "4:REVENUE:15000.00:2024-Q2",
    "5:COST:-3000.00:2024-Q2",
    "6:HEADCOUNT:7:2024-Q2",
]


def test_pipeline_returns_string_on_success():
    result = run_pipeline(SAMPLE_LINES)
    assert isinstance(result, str)


def test_pipeline_contains_all_periods():
    result = run_pipeline(SAMPLE_LINES)
    assert "2024-Q1" in result
    assert "2024-Q2" in result


def test_pipeline_contains_all_categories():
    result = run_pipeline(SAMPLE_LINES)
    assert "REVENUE" in result
    assert "COST" in result
    assert "HEADCOUNT" in result


def test_pipeline_contains_total():
    result = run_pipeline(SAMPLE_LINES)
    assert "TOTAL" in result


def test_pipeline_parse_error_propagates():
    lines = ["bad_line"]
    result = run_pipeline(lines)
    assert isinstance(result, ParseError)


def test_pipeline_parse_error_on_negative_revenue():
    lines = ["1:REVENUE:-100:2024-Q1"]
    result = run_pipeline(lines)
    assert isinstance(result, ParseError)


def test_pipeline_single_row():
    result = run_pipeline(["1:REVENUE:1000:2024-Q1"])
    assert isinstance(result, str)
    assert "2024-Q1" in result
    assert "$1,000.00" in result


def test_pipeline_headcount_plain_integer():
    result = run_pipeline(["1:HEADCOUNT:15:2024-Q1"])
    assert isinstance(result, str)
    assert "15" in result


def test_pipeline_cost_negative():
    result = run_pipeline(["1:COST:-500:2024-Q1"])
    assert isinstance(result, str)
    assert "-$500.00" in result


def test_pipeline_multi_year_periods():
    lines = [
        "1:REVENUE:1000:2023-Q4",
        "2:REVENUE:2000:2024-Q1",
    ]
    result = run_pipeline(lines)
    assert isinstance(result, str)
    header = result.splitlines()[0]
    idx_2023q4 = header.index("2023-Q4")
    idx_2024q1 = header.index("2024-Q1")
    assert idx_2023q4 < idx_2024q1


def test_pipeline_empty_input():
    # Empty input should produce an empty-ish result or handle gracefully
    # With zero rows, aggregate returns empty data; format returns minimal table
    result = run_pipeline([])
    # Either a string or an error is acceptable; just shouldn't raise
    assert isinstance(result, (str, ParseError, ValidationError))
