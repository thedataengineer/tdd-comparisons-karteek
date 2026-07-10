"""Tests for the aggregate stage."""

import pytest
from decimal import Decimal

from report_pipeline.parse import ParsedRow
from report_pipeline.aggregate import aggregate, AggregatedData


def make_row(row_id, category, value, period):
    return ParsedRow(row_id=row_id, category=category, value=Decimal(str(value)), period=period)


# ---------- Basic aggregation ----------

def test_aggregate_single_row():
    rows = [make_row(1, "REVENUE", 1000, "2024-Q1")]
    data = aggregate(rows)
    assert data.periods == ["2024-Q1"]
    assert data.categories == ["REVENUE"]
    assert data.cells[("2024-Q1", "REVENUE")] == Decimal("1000")
    assert data.period_subtotals["2024-Q1"] == Decimal("1000")
    assert data.category_totals["REVENUE"] == Decimal("1000")
    assert data.grand_total == Decimal("1000")


def test_aggregate_multiple_categories_same_period():
    rows = [
        make_row(1, "REVENUE", 1000, "2024-Q1"),
        make_row(2, "COST", -200, "2024-Q1"),
        make_row(3, "HEADCOUNT", 5, "2024-Q1"),
    ]
    data = aggregate(rows)
    assert data.cells[("2024-Q1", "REVENUE")] == Decimal("1000")
    assert data.cells[("2024-Q1", "COST")] == Decimal("-200")
    assert data.cells[("2024-Q1", "HEADCOUNT")] == Decimal("5")
    assert data.period_subtotals["2024-Q1"] == Decimal("805")
    assert data.grand_total == Decimal("805")


def test_aggregate_multiple_periods():
    rows = [
        make_row(1, "REVENUE", 1000, "2024-Q1"),
        make_row(2, "REVENUE", 2000, "2024-Q2"),
    ]
    data = aggregate(rows)
    assert data.periods == ["2024-Q1", "2024-Q2"]
    assert data.category_totals["REVENUE"] == Decimal("3000")
    assert data.grand_total == Decimal("3000")


def test_aggregate_periods_sorted_chronologically():
    rows = [
        make_row(1, "REVENUE", 100, "2024-Q3"),
        make_row(2, "REVENUE", 200, "2024-Q1"),
        make_row(3, "REVENUE", 300, "2023-Q4"),
    ]
    data = aggregate(rows)
    assert data.periods == ["2023-Q4", "2024-Q1", "2024-Q3"]


def test_aggregate_categories_in_canonical_order():
    rows = [
        make_row(1, "HEADCOUNT", 10, "2024-Q1"),
        make_row(2, "REVENUE", 500, "2024-Q1"),
        make_row(3, "COST", -100, "2024-Q1"),
    ]
    data = aggregate(rows)
    assert data.categories == ["REVENUE", "COST", "HEADCOUNT"]


def test_aggregate_sums_multiple_rows_same_period_category():
    rows = [
        make_row(1, "REVENUE", 1000, "2024-Q1"),
        make_row(2, "REVENUE", 500, "2024-Q1"),
    ]
    data = aggregate(rows)
    assert data.cells[("2024-Q1", "REVENUE")] == Decimal("1500")
    assert data.category_totals["REVENUE"] == Decimal("1500")


def test_aggregate_missing_cell_not_in_dict():
    rows = [
        make_row(1, "REVENUE", 1000, "2024-Q1"),
        make_row(2, "COST", -200, "2024-Q2"),
    ]
    data = aggregate(rows)
    # (2024-Q1, COST) was never added
    assert ("2024-Q1", "COST") not in data.cells


def test_aggregate_partial_categories_only_revenue():
    rows = [make_row(1, "REVENUE", 999, "2024-Q1")]
    data = aggregate(rows)
    assert data.categories == ["REVENUE"]
    assert "COST" not in data.categories
    assert "HEADCOUNT" not in data.categories


def test_aggregate_grand_total_multi_period_multi_category():
    rows = [
        make_row(1, "REVENUE", 1000, "2024-Q1"),
        make_row(2, "COST", -300, "2024-Q1"),
        make_row(3, "REVENUE", 2000, "2024-Q2"),
        make_row(4, "COST", -500, "2024-Q2"),
    ]
    data = aggregate(rows)
    assert data.grand_total == Decimal("2200")  # (1000-300) + (2000-500)
