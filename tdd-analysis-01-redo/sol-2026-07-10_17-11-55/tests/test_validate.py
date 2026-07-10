"""Tests for the validate_output stage of the report pipeline."""
from decimal import Decimal
import pytest
from report_pipeline.validate_output import validate_output
from report_pipeline.format_table import format_table


def make_aggregated(cells_dict, periods, categories):
    cells = {k: Decimal(str(v)) for k, v in cells_dict.items()}
    period_totals = {}
    for p in periods:
        period_totals[p] = sum(cells.get((p, c), Decimal("0")) for c in categories)
    category_totals = {}
    for c in categories:
        category_totals[c] = sum(cells.get((p, c), Decimal("0")) for p in periods)
    return {
        "cells": cells,
        "periods": periods,
        "categories": categories,
        "period_totals": period_totals,
        "category_totals": category_totals,
    }


class TestValidateOutputSuccess:
    def test_valid_table_returns_string(self):
        agg = make_aggregated(
            {("2024-Q1", "REVENUE"): "1000.00"},
            ["2024-Q1"], ["REVENUE"]
        )
        table = format_table(agg)
        result = validate_output(table, agg)
        assert isinstance(result, str)
        assert result == table

    def test_valid_multi_period_table(self):
        agg = make_aggregated(
            {
                ("2024-Q1", "REVENUE"): "1000.00",
                ("2024-Q2", "REVENUE"): "2000.00",
                ("2024-Q1", "COST"): "-500.00",
                ("2024-Q2", "COST"): "-300.00",
            },
            ["2024-Q1", "2024-Q2"], ["REVENUE", "COST"]
        )
        table = format_table(agg)
        result = validate_output(table, agg)
        assert result == table

    def test_valid_all_categories(self):
        agg = make_aggregated(
            {
                ("2024-Q1", "REVENUE"): "5000.00",
                ("2024-Q1", "COST"): "-1000.00",
                ("2024-Q1", "HEADCOUNT"): "50",
            },
            ["2024-Q1"], ["REVENUE", "COST", "HEADCOUNT"]
        )
        table = format_table(agg)
        result = validate_output(table, agg)
        assert result == table


class TestValidateOutputErrors:
    def _assert_error(self, result, reason_contains=None):
        assert isinstance(result, dict)
        assert result.get("stage") == "validate_output"
        assert "reason" in result
        if reason_contains:
            assert reason_contains.lower() in result["reason"].lower()

    def test_missing_period_column(self):
        agg = make_aggregated(
            {("2024-Q1", "REVENUE"): "1000.00"},
            ["2024-Q1"], ["REVENUE"]
        )
        table = format_table(agg)
        # Remove a period from the table
        bad_table = table.replace("2024-Q1", "")
        result = validate_output(bad_table, agg)
        self._assert_error(result, "period")

    def test_column_narrower_than_header(self):
        agg = make_aggregated(
            {("2024-Q1", "REVENUE"): "1000.00"},
            ["2024-Q1"], ["REVENUE"]
        )
        table = format_table(agg)
        # Artificially truncate columns (make header col narrower than data)
        # This is contrived - we just test the validator detects it
        lines = table.strip().split("\n")
        # We'll test with a manually crafted bad table
        bad_table = "CAT  2024\nREVENUE  $1,000.00\nTOTAL  $1,000.00"
        result = validate_output(bad_table, agg)
        self._assert_error(result)

    def test_total_column_mismatch(self):
        agg = make_aggregated(
            {
                ("2024-Q1", "REVENUE"): "1000.00",
                ("2024-Q2", "REVENUE"): "2000.00",
            },
            ["2024-Q1", "2024-Q2"], ["REVENUE"]
        )
        table = format_table(agg)
        # Corrupt the TOTAL column value
        bad_table = table.replace("$3,000.00", "$9,999.00")
        result = validate_output(bad_table, agg)
        self._assert_error(result, "total")


class TestValidateOutputEdgeCases:
    def _assert_error(self, result, reason_contains=None):
        assert isinstance(result, dict)
        assert result.get("stage") == "validate_output"
        if reason_contains:
            assert reason_contains.lower() in result["reason"].lower()

    def test_missing_total_column(self):
        agg = make_aggregated(
            {("2024-Q1", "REVENUE"): "1000.00"},
            ["2024-Q1"], ["REVENUE"]
        )
        table = format_table(agg)
        # Remove the TOTAL header
        bad_table = table.replace("TOTAL", "XXXXX")
        result = validate_output(bad_table, agg)
        self._assert_error(result, "total")

    def test_empty_periods_valid(self):
        """Empty aggregated data should produce a valid (empty) result."""
        agg = make_aggregated({}, [], [])
        table = format_table(agg)
        result = validate_output(table, agg)
        # Should return the table (no periods to validate)
        assert result == table

    def test_total_col_index_out_of_range(self):
        """Crafted table where TOTAL col index exceeds row data cols."""
        # Build a table that has only 1 data column (TOTAL) but rows with no data
        bad_table = "CATEGORY  2024-Q1  TOTAL\nREVENUE  $1,000.00\nTOTAL  $1,000.00"
        agg = make_aggregated(
            {("2024-Q1", "REVENUE"): "1000.00"},
            ["2024-Q1"], ["REVENUE"]
        )
        result = validate_output(bad_table, agg)
        # This is a malformed table - should either error or validate
        # The important thing is it doesn't crash
        assert result is not None


class TestValidateOutputIntegration:
    def test_pipeline_format_then_validate(self):
        """Validate round-trips correctly for various inputs."""
        from report_pipeline.parse import parse
        from report_pipeline.aggregate import aggregate

        raw = [
            "1:REVENUE:10000.00:2024-Q1",
            "2:REVENUE:20000.00:2024-Q2",
            "3:COST:-3000.00:2024-Q1",
            "4:COST:-4000.00:2024-Q2",
            "5:HEADCOUNT:100:2024-Q1",
            "6:HEADCOUNT:110:2024-Q2",
        ]
        parsed = parse(raw)
        agg = aggregate(parsed)
        table = format_table(agg)
        result = validate_output(table, agg)
        assert result == table
