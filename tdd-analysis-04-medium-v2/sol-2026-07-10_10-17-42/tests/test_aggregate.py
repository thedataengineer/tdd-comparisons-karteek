"""Tests for the aggregate stage."""

from decimal import Decimal
import pytest

from report_pipeline.models import ParsedRow, AggregatedData
from report_pipeline.aggregate import aggregate


def make_row(row_id, category, value, period):
    return ParsedRow(row_id=row_id, category=category, value=Decimal(value), period=period)


def test_aggregate_single_row():
    rows = [make_row(1, "REVENUE", "1000.00", "2024-Q1")]
    result = aggregate(rows)
    assert isinstance(result, AggregatedData)
    assert result.periods == ["2024-Q1"]
    assert "REVENUE" in result.categories
    assert result.values["2024-Q1"]["REVENUE"] == Decimal("1000.00")


def test_aggregate_sums_same_period_category():
    rows = [
        make_row(1, "REVENUE", "1000.00", "2024-Q1"),
        make_row(2, "REVENUE", "500.00", "2024-Q1"),
    ]
    result = aggregate(rows)
    assert result.values["2024-Q1"]["REVENUE"] == Decimal("1500.00")


def test_aggregate_periods_in_chronological_order():
    rows = [
        make_row(1, "REVENUE", "100.00", "2024-Q3"),
        make_row(2, "REVENUE", "200.00", "2023-Q4"),
        make_row(3, "REVENUE", "300.00", "2024-Q1"),
    ]
    result = aggregate(rows)
    assert result.periods == ["2023-Q4", "2024-Q1", "2024-Q3"]


def test_aggregate_categories_in_spec_order():
    rows = [
        make_row(1, "HEADCOUNT", "10", "2024-Q1"),
        make_row(2, "COST", "-100.00", "2024-Q1"),
        make_row(3, "REVENUE", "500.00", "2024-Q1"),
    ]
    result = aggregate(rows)
    assert result.categories == ["REVENUE", "COST", "HEADCOUNT"]


def test_aggregate_period_totals():
    rows = [
        make_row(1, "REVENUE", "1000.00", "2024-Q1"),
        make_row(2, "COST", "-200.00", "2024-Q1"),
        make_row(3, "HEADCOUNT", "5", "2024-Q1"),
    ]
    result = aggregate(rows)
    # period total = 1000 + (-200) + 5 = 805
    assert result.period_totals["2024-Q1"] == Decimal("805")


def test_aggregate_category_totals():
    rows = [
        make_row(1, "REVENUE", "1000.00", "2024-Q1"),
        make_row(2, "REVENUE", "2000.00", "2024-Q2"),
    ]
    result = aggregate(rows)
    assert result.category_totals["REVENUE"] == Decimal("3000.00")


def test_aggregate_grand_total():
    rows = [
        make_row(1, "REVENUE", "1000.00", "2024-Q1"),
        make_row(2, "COST", "-200.00", "2024-Q1"),
    ]
    result = aggregate(rows)
    assert result.grand_total == Decimal("800.00")


def test_aggregate_missing_category_filled_with_zero():
    """If a period has no COST rows, COST should be zero for that period."""
    rows = [
        make_row(1, "REVENUE", "1000.00", "2024-Q1"),
        make_row(2, "COST", "-50.00", "2024-Q2"),
    ]
    result = aggregate(rows)
    assert result.values["2024-Q1"]["COST"] == Decimal("0")
    assert result.values["2024-Q2"]["REVENUE"] == Decimal("0")


def test_aggregate_single_period_multiple_categories():
    rows = [
        make_row(1, "REVENUE", "5000.00", "2023-Q4"),
        make_row(2, "COST", "-1500.00", "2023-Q4"),
        make_row(3, "HEADCOUNT", "20", "2023-Q4"),
    ]
    result = aggregate(rows)
    assert result.period_totals["2023-Q4"] == Decimal("3520")
    assert result.grand_total == Decimal("3520")
    assert result.category_totals["REVENUE"] == Decimal("5000.00")
    assert result.category_totals["COST"] == Decimal("-1500.00")
    assert result.category_totals["HEADCOUNT"] == Decimal("20")
