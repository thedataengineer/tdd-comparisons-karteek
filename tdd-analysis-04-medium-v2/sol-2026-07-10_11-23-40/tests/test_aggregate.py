"""Tests for the aggregate stage."""
from decimal import Decimal

import pytest

from report_pipeline import AggregatedData, ParsedRow, aggregate


def _rows(*specs):
    """Helper to build ParsedRow list from (id, cat, value_str, period) tuples."""
    return [
        ParsedRow(row_id=i, category=cat, value=Decimal(val), period=period)
        for i, (cat, val, period) in enumerate(specs, start=1)
    ]


def test_aggregate_periods_chronological_order():
    rows = _rows(
        ("REVENUE", "500", "2024-Q2"),
        ("REVENUE", "300", "2023-Q4"),
        ("REVENUE", "200", "2024-Q1"),
    )
    result = aggregate(rows)
    assert result.periods == ["2023-Q4", "2024-Q1", "2024-Q2"]


def test_aggregate_categories_in_spec_order():
    rows = _rows(
        ("HEADCOUNT", "5", "2024-Q1"),
        ("COST", "-100", "2024-Q1"),
        ("REVENUE", "500", "2024-Q1"),
    )
    result = aggregate(rows)
    assert result.categories == ["REVENUE", "COST", "HEADCOUNT"]


def test_aggregate_sums_within_period_category():
    rows = _rows(
        ("REVENUE", "1000", "2024-Q1"),
        ("REVENUE", "500", "2024-Q1"),
    )
    result = aggregate(rows)
    assert result.period_category[("2024-Q1", "REVENUE")] == Decimal("1500")


def test_aggregate_period_totals():
    rows = _rows(
        ("REVENUE", "1000", "2024-Q1"),
        ("COST", "-200", "2024-Q1"),
        ("HEADCOUNT", "10", "2024-Q1"),
    )
    result = aggregate(rows)
    assert result.period_totals["2024-Q1"] == Decimal("810")


def test_aggregate_category_totals_across_periods():
    rows = _rows(
        ("REVENUE", "1000", "2024-Q1"),
        ("REVENUE", "2000", "2024-Q2"),
    )
    result = aggregate(rows)
    assert result.category_totals["REVENUE"] == Decimal("3000")
    assert result.grand_total == Decimal("3000")


def test_aggregate_missing_category_for_period_defaults_zero():
    """If a period has no COST row, that (period, COST) combination is absent from period_category."""
    rows = _rows(
        ("REVENUE", "500", "2024-Q1"),
        ("COST", "-100", "2024-Q2"),
    )
    result = aggregate(rows)
    # period_category should not have a key for (2024-Q1, COST)
    assert ("2024-Q1", "COST") not in result.period_category
    # period totals should still work
    assert result.period_totals["2024-Q1"] == Decimal("500")
    assert result.period_totals["2024-Q2"] == Decimal("-100")


def test_aggregate_single_row():
    rows = _rows(("REVENUE", "1000.00", "2024-Q1"))
    result = aggregate(rows)
    assert isinstance(result, AggregatedData)
    assert result.periods == ["2024-Q1"]
    assert result.categories == ["REVENUE"]
    assert result.period_category[("2024-Q1", "REVENUE")] == Decimal("1000.00")
    assert result.period_totals["2024-Q1"] == Decimal("1000.00")
    assert result.category_totals["REVENUE"] == Decimal("1000.00")
    assert result.grand_total == Decimal("1000.00")
