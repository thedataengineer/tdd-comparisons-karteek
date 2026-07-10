"""Tests for the aggregate stage."""

import pytest
from report_pipeline.parse import ParsedRow
from report_pipeline.aggregate import aggregate, AggregatedData, CATEGORY_ORDER


def _row(row_id, category, value, period):
    return ParsedRow(row_id=row_id, category=category, value=value, period=period)


# ── Basic structure ───────────────────────────────────────────────────────────

def test_aggregate_returns_aggregated_data():
    rows = [_row(1, "REVENUE", 1000.0, "2024-Q1")]
    result = aggregate(rows)
    assert isinstance(result, AggregatedData)


def test_aggregate_single_row():
    rows = [_row(1, "REVENUE", 500.0, "2024-Q1")]
    agg = aggregate(rows)
    assert agg.periods == ["2024-Q1"]
    assert agg.categories == ["REVENUE"]
    assert agg.period_category["2024-Q1"]["REVENUE"] == pytest.approx(500.0)
    assert agg.category_totals["REVENUE"] == pytest.approx(500.0)
    assert agg.period_subtotals["2024-Q1"] == pytest.approx(500.0)
    assert agg.grand_total == pytest.approx(500.0)


def test_aggregate_sums_same_period_and_category():
    rows = [
        _row(1, "REVENUE", 300.0, "2024-Q1"),
        _row(2, "REVENUE", 700.0, "2024-Q1"),
    ]
    agg = aggregate(rows)
    assert agg.period_category["2024-Q1"]["REVENUE"] == pytest.approx(1000.0)
    assert agg.category_totals["REVENUE"] == pytest.approx(1000.0)


def test_aggregate_period_ordering():
    rows = [
        _row(1, "REVENUE", 100.0, "2024-Q3"),
        _row(2, "REVENUE", 200.0, "2023-Q1"),
        _row(3, "REVENUE", 150.0, "2024-Q1"),
    ]
    agg = aggregate(rows)
    assert agg.periods == ["2023-Q1", "2024-Q1", "2024-Q3"]


def test_aggregate_period_ordering_across_years():
    rows = [
        _row(1, "REVENUE", 100.0, "2025-Q1"),
        _row(2, "REVENUE", 200.0, "2024-Q4"),
    ]
    agg = aggregate(rows)
    assert agg.periods == ["2024-Q4", "2025-Q1"]


def test_aggregate_category_ordering():
    rows = [
        _row(1, "HEADCOUNT", 5.0, "2024-Q1"),
        _row(2, "COST", -100.0, "2024-Q1"),
        _row(3, "REVENUE", 500.0, "2024-Q1"),
    ]
    agg = aggregate(rows)
    assert agg.categories == ["REVENUE", "COST", "HEADCOUNT"]


def test_aggregate_missing_cells_filled_with_zero():
    rows = [
        _row(1, "REVENUE", 500.0, "2024-Q1"),
        _row(2, "COST", -100.0, "2024-Q2"),
    ]
    agg = aggregate(rows)
    # REVENUE in Q2 should be 0
    assert agg.period_category["2024-Q2"]["REVENUE"] == pytest.approx(0.0)
    # COST in Q1 should be 0
    assert agg.period_category["2024-Q1"]["COST"] == pytest.approx(0.0)


def test_aggregate_period_subtotals():
    rows = [
        _row(1, "REVENUE", 1000.0, "2024-Q1"),
        _row(2, "COST", -200.0, "2024-Q1"),
        _row(3, "HEADCOUNT", 10.0, "2024-Q1"),
    ]
    agg = aggregate(rows)
    assert agg.period_subtotals["2024-Q1"] == pytest.approx(810.0)


def test_aggregate_category_totals_across_periods():
    rows = [
        _row(1, "REVENUE", 100.0, "2024-Q1"),
        _row(2, "REVENUE", 200.0, "2024-Q2"),
    ]
    agg = aggregate(rows)
    assert agg.category_totals["REVENUE"] == pytest.approx(300.0)


def test_aggregate_grand_total():
    rows = [
        _row(1, "REVENUE", 1000.0, "2024-Q1"),
        _row(2, "COST", -300.0, "2024-Q1"),
        _row(3, "HEADCOUNT", 5.0, "2024-Q1"),
    ]
    agg = aggregate(rows)
    assert agg.grand_total == pytest.approx(705.0)


def test_aggregate_only_present_categories_included():
    rows = [_row(1, "REVENUE", 100.0, "2024-Q1")]
    agg = aggregate(rows)
    assert "COST" not in agg.categories
    assert "HEADCOUNT" not in agg.categories


def test_aggregate_multiple_periods_multiple_categories():
    rows = [
        _row(1, "REVENUE", 1000.0, "2024-Q1"),
        _row(2, "REVENUE", 2000.0, "2024-Q2"),
        _row(3, "COST", -500.0, "2024-Q1"),
        _row(4, "COST", -300.0, "2024-Q2"),
        _row(5, "HEADCOUNT", 10.0, "2024-Q1"),
        _row(6, "HEADCOUNT", 12.0, "2024-Q2"),
    ]
    agg = aggregate(rows)
    assert agg.periods == ["2024-Q1", "2024-Q2"]
    assert agg.categories == ["REVENUE", "COST", "HEADCOUNT"]
    assert agg.category_totals["REVENUE"] == pytest.approx(3000.0)
    assert agg.category_totals["COST"] == pytest.approx(-800.0)
    assert agg.category_totals["HEADCOUNT"] == pytest.approx(22.0)
    assert agg.grand_total == pytest.approx(2222.0)
