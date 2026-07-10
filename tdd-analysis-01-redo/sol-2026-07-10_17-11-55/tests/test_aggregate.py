"""Tests for the aggregate stage of the report pipeline."""
from decimal import Decimal
import pytest
from report_pipeline.aggregate import aggregate


def make_row(row_id, category, value, period):
    return {"row_id": row_id, "category": category, "value": Decimal(str(value)), "period": period}


class TestAggregateStructure:
    def test_returns_dict_with_required_keys(self):
        rows = [make_row(1, "REVENUE", "1000", "2024-Q1")]
        result = aggregate(rows)
        assert "cells" in result
        assert "period_totals" in result
        assert "category_totals" in result
        assert "periods" in result
        assert "categories" in result

    def test_periods_ordered_chronologically(self):
        rows = [
            make_row(1, "REVENUE", "1000", "2024-Q2"),
            make_row(2, "REVENUE", "2000", "2023-Q4"),
            make_row(3, "REVENUE", "3000", "2024-Q1"),
        ]
        result = aggregate(rows)
        assert result["periods"] == ["2023-Q4", "2024-Q1", "2024-Q2"]

    def test_categories_in_fixed_order(self):
        rows = [
            make_row(1, "HEADCOUNT", "10", "2024-Q1"),
            make_row(2, "COST", "500", "2024-Q1"),
            make_row(3, "REVENUE", "1000", "2024-Q1"),
        ]
        result = aggregate(rows)
        assert result["categories"] == ["REVENUE", "COST", "HEADCOUNT"]

    def test_categories_only_present_categories(self):
        rows = [make_row(1, "REVENUE", "1000", "2024-Q1")]
        result = aggregate(rows)
        assert result["categories"] == ["REVENUE"]

    def test_categories_two_present(self):
        rows = [
            make_row(1, "REVENUE", "1000", "2024-Q1"),
            make_row(2, "COST", "500", "2024-Q1"),
        ]
        result = aggregate(rows)
        assert result["categories"] == ["REVENUE", "COST"]


class TestAggregateCells:
    def test_single_cell(self):
        rows = [make_row(1, "REVENUE", "1000", "2024-Q1")]
        result = aggregate(rows)
        assert result["cells"][("2024-Q1", "REVENUE")] == Decimal("1000")

    def test_sums_multiple_rows_same_period_category(self):
        rows = [
            make_row(1, "REVENUE", "1000", "2024-Q1"),
            make_row(2, "REVENUE", "500", "2024-Q1"),
        ]
        result = aggregate(rows)
        assert result["cells"][("2024-Q1", "REVENUE")] == Decimal("1500")

    def test_missing_combination_defaults_to_zero(self):
        rows = [make_row(1, "REVENUE", "1000", "2024-Q1")]
        result = aggregate(rows)
        assert result["cells"].get(("2024-Q1", "COST"), Decimal("0")) == Decimal("0")

    def test_negative_cost_value(self):
        rows = [make_row(1, "COST", "-200", "2024-Q1")]
        result = aggregate(rows)
        assert result["cells"][("2024-Q1", "COST")] == Decimal("-200")

    def test_multiple_periods_same_category(self):
        rows = [
            make_row(1, "REVENUE", "1000", "2024-Q1"),
            make_row(2, "REVENUE", "2000", "2024-Q2"),
        ]
        result = aggregate(rows)
        assert result["cells"][("2024-Q1", "REVENUE")] == Decimal("1000")
        assert result["cells"][("2024-Q2", "REVENUE")] == Decimal("2000")


class TestAggregatePeriodTotals:
    def test_single_period_single_category(self):
        rows = [make_row(1, "REVENUE", "1000", "2024-Q1")]
        result = aggregate(rows)
        assert result["period_totals"]["2024-Q1"] == Decimal("1000")

    def test_single_period_multiple_categories(self):
        rows = [
            make_row(1, "REVENUE", "1000", "2024-Q1"),
            make_row(2, "COST", "-200", "2024-Q1"),
            make_row(3, "HEADCOUNT", "10", "2024-Q1"),
        ]
        result = aggregate(rows)
        assert result["period_totals"]["2024-Q1"] == Decimal("810")

    def test_multiple_periods(self):
        rows = [
            make_row(1, "REVENUE", "1000", "2024-Q1"),
            make_row(2, "REVENUE", "2000", "2024-Q2"),
        ]
        result = aggregate(rows)
        assert result["period_totals"]["2024-Q1"] == Decimal("1000")
        assert result["period_totals"]["2024-Q2"] == Decimal("2000")


class TestAggregateCategoryTotals:
    def test_single_category_single_period(self):
        rows = [make_row(1, "REVENUE", "1000", "2024-Q1")]
        result = aggregate(rows)
        assert result["category_totals"]["REVENUE"] == Decimal("1000")

    def test_single_category_multiple_periods(self):
        rows = [
            make_row(1, "REVENUE", "1000", "2024-Q1"),
            make_row(2, "REVENUE", "2000", "2024-Q2"),
        ]
        result = aggregate(rows)
        assert result["category_totals"]["REVENUE"] == Decimal("3000")

    def test_multiple_categories(self):
        rows = [
            make_row(1, "REVENUE", "5000", "2024-Q1"),
            make_row(2, "COST", "-1000", "2024-Q1"),
        ]
        result = aggregate(rows)
        assert result["category_totals"]["REVENUE"] == Decimal("5000")
        assert result["category_totals"]["COST"] == Decimal("-1000")

    def test_headcount_total(self):
        rows = [
            make_row(1, "HEADCOUNT", "10", "2024-Q1"),
            make_row(2, "HEADCOUNT", "5", "2024-Q2"),
        ]
        result = aggregate(rows)
        assert result["category_totals"]["HEADCOUNT"] == Decimal("15")


class TestAggregateEmpty:
    def test_empty_input(self):
        result = aggregate([])
        assert result["periods"] == []
        assert result["categories"] == []
        assert result["cells"] == {}
        assert result["period_totals"] == {}
        assert result["category_totals"] == {}
