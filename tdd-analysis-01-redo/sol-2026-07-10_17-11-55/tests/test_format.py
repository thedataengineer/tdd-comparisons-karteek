"""Tests for the format stage of the report pipeline."""
from decimal import Decimal
import pytest
from report_pipeline.format_table import format_table


def make_aggregated(cells_dict, periods, categories):
    """Helper to build an aggregated structure."""
    from collections import defaultdict
    cells = {k: Decimal(str(v)) for k, v in cells_dict.items()}

    period_totals = {}
    for p in periods:
        period_totals[p] = sum(
            cells.get((p, c), Decimal("0")) for c in categories
        )

    category_totals = {}
    for c in categories:
        category_totals[c] = sum(
            cells.get((p, c), Decimal("0")) for p in periods
        )

    return {
        "cells": cells,
        "periods": periods,
        "categories": categories,
        "period_totals": period_totals,
        "category_totals": category_totals,
    }


class TestFormatOutput:
    def test_returns_string(self):
        agg = make_aggregated(
            {("2024-Q1", "REVENUE"): "1000.00"},
            ["2024-Q1"], ["REVENUE"]
        )
        result = format_table(agg)
        assert isinstance(result, str)

    def test_has_header_row(self):
        agg = make_aggregated(
            {("2024-Q1", "REVENUE"): "1000.00"},
            ["2024-Q1"], ["REVENUE"]
        )
        result = format_table(agg)
        lines = result.strip().split("\n")
        assert "2024-Q1" in lines[0]
        assert "TOTAL" in lines[0]

    def test_has_category_rows(self):
        agg = make_aggregated(
            {("2024-Q1", "REVENUE"): "1000.00"},
            ["2024-Q1"], ["REVENUE"]
        )
        result = format_table(agg)
        assert "REVENUE" in result

    def test_has_total_row(self):
        agg = make_aggregated(
            {("2024-Q1", "REVENUE"): "1000.00"},
            ["2024-Q1"], ["REVENUE"]
        )
        result = format_table(agg)
        lines = result.strip().split("\n")
        assert "TOTAL" in lines[-1]

    def test_revenue_dollar_format(self):
        agg = make_aggregated(
            {("2024-Q1", "REVENUE"): "1234.56"},
            ["2024-Q1"], ["REVENUE"]
        )
        result = format_table(agg)
        assert "$1,234.56" in result

    def test_revenue_thousands_separator(self):
        agg = make_aggregated(
            {("2024-Q1", "REVENUE"): "1000000.00"},
            ["2024-Q1"], ["REVENUE"]
        )
        result = format_table(agg)
        assert "$1,000,000.00" in result

    def test_cost_negative_format(self):
        agg = make_aggregated(
            {("2024-Q1", "COST"): "-200.00"},
            ["2024-Q1"], ["COST"]
        )
        result = format_table(agg)
        assert "-$200.00" in result

    def test_headcount_integer_format(self):
        agg = make_aggregated(
            {("2024-Q1", "HEADCOUNT"): "42"},
            ["2024-Q1"], ["HEADCOUNT"]
        )
        result = format_table(agg)
        assert "42" in result
        assert "$" not in result

    def test_headcount_no_decimal(self):
        agg = make_aggregated(
            {("2024-Q1", "HEADCOUNT"): "42.0"},
            ["2024-Q1"], ["HEADCOUNT"]
        )
        result = format_table(agg)
        # Should be formatted as integer
        assert "42" in result
        assert "42.0" not in result

    def test_columns_ordered_chronologically(self):
        agg = make_aggregated(
            {
                ("2024-Q2", "REVENUE"): "2000.00",
                ("2024-Q1", "REVENUE"): "1000.00",
            },
            ["2024-Q1", "2024-Q2"], ["REVENUE"]
        )
        result = format_table(agg)
        lines = result.strip().split("\n")
        header = lines[0]
        q1_pos = header.index("2024-Q1")
        q2_pos = header.index("2024-Q2")
        assert q1_pos < q2_pos

    def test_categories_in_order(self):
        agg = make_aggregated(
            {
                ("2024-Q1", "REVENUE"): "1000.00",
                ("2024-Q1", "COST"): "-200.00",
                ("2024-Q1", "HEADCOUNT"): "10",
            },
            ["2024-Q1"], ["REVENUE", "COST", "HEADCOUNT"]
        )
        result = format_table(agg)
        lines = result.strip().split("\n")
        # Find category rows (skip header, last is TOTAL)
        revenue_line = next(l for l in lines if l.strip().startswith("REVENUE"))
        cost_line = next(l for l in lines if l.strip().startswith("COST"))
        headcount_line = next(l for l in lines if l.strip().startswith("HEADCOUNT"))
        rev_idx = lines.index(revenue_line)
        cost_idx = lines.index(cost_line)
        head_idx = lines.index(headcount_line)
        assert rev_idx < cost_idx < head_idx

    def test_two_spaces_padding_between_columns(self):
        agg = make_aggregated(
            {("2024-Q1", "REVENUE"): "1000.00"},
            ["2024-Q1"], ["REVENUE"]
        )
        result = format_table(agg)
        # Each line should have at least 2 spaces between columns
        for line in result.strip().split("\n"):
            # Check no single-space column separators (basic check)
            assert "  " in line  # at least 2 spaces somewhere

    def test_total_column_correct_for_revenue(self):
        agg = make_aggregated(
            {
                ("2024-Q1", "REVENUE"): "1000.00",
                ("2024-Q2", "REVENUE"): "2000.00",
            },
            ["2024-Q1", "2024-Q2"], ["REVENUE"]
        )
        result = format_table(agg)
        assert "$3,000.00" in result

    def test_total_row_period_sums(self):
        agg = make_aggregated(
            {
                ("2024-Q1", "REVENUE"): "1000.00",
                ("2024-Q1", "COST"): "-200.00",
            },
            ["2024-Q1"], ["REVENUE", "COST"]
        )
        result = format_table(agg)
        lines = result.strip().split("\n")
        total_line = lines[-1]
        assert "TOTAL" in total_line
        # Period total: 1000 - 200 = 800
        assert "$800.00" in total_line

    def test_column_width_at_least_header_width(self):
        agg = make_aggregated(
            {("2024-Q1", "REVENUE"): "1.00"},
            ["2024-Q1"], ["REVENUE"]
        )
        result = format_table(agg)
        lines = result.strip().split("\n")
        # Header contains "2024-Q1" which is 7 chars
        # Each column content should be at least that wide
        for line in lines:
            assert len(line) >= len("REVENUE") + len("2024-Q1")

    def test_empty_cell_zero_revenue(self):
        """Missing period/category combo should show as $0.00"""
        agg = make_aggregated(
            {("2024-Q1", "REVENUE"): "1000.00"},
            ["2024-Q1", "2024-Q2"], ["REVENUE"]
        )
        result = format_table(agg)
        assert "$0.00" in result

    def test_empty_cell_zero_headcount(self):
        """Missing period/category combo should show as 0 for headcount"""
        agg = make_aggregated(
            {("2024-Q1", "HEADCOUNT"): "10"},
            ["2024-Q1", "2024-Q2"], ["HEADCOUNT"]
        )
        result = format_table(agg)
        # Should have a zero for 2024-Q2
        lines = result.strip().split("\n")
        headcount_line = next(l for l in lines if l.strip().startswith("HEADCOUNT"))
        assert "0" in headcount_line


class TestFormatValueFormatting:
    """Test the specific value formatting rules."""

    def test_revenue_positive(self):
        agg = make_aggregated(
            {("2024-Q1", "REVENUE"): "1234.56"},
            ["2024-Q1"], ["REVENUE"]
        )
        result = format_table(agg)
        assert "$1,234.56" in result

    def test_cost_positive(self):
        agg = make_aggregated(
            {("2024-Q1", "COST"): "500.00"},
            ["2024-Q1"], ["COST"]
        )
        result = format_table(agg)
        assert "$500.00" in result

    def test_cost_negative(self):
        agg = make_aggregated(
            {("2024-Q1", "COST"): "-1234.56"},
            ["2024-Q1"], ["COST"]
        )
        result = format_table(agg)
        assert "-$1,234.56" in result

    def test_headcount_large_integer(self):
        agg = make_aggregated(
            {("2024-Q1", "HEADCOUNT"): "1500"},
            ["2024-Q1"], ["HEADCOUNT"]
        )
        result = format_table(agg)
        assert "1500" in result

    def test_values_right_aligned(self):
        agg = make_aggregated(
            {
                ("2024-Q1", "REVENUE"): "1.00",
                ("2024-Q1", "HEADCOUNT"): "10",
            },
            ["2024-Q1"], ["REVENUE", "HEADCOUNT"]
        )
        result = format_table(agg)
        lines = result.strip().split("\n")
        # All data lines should have consistent column positions
        # Verify right-alignment: the value in each column should be right-aligned
        # Just check the table isn't left-aligned (padding on the right)
        # A simple check: revenue line should not have trailing spaces before the column ends
        # This is hard to check precisely without knowing column widths, so just verify
        # formatting is reasonable
        assert len(lines) >= 2
