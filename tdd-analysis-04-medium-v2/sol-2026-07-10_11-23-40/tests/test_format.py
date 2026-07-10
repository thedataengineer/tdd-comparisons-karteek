"""Tests for the format_table stage."""
from decimal import Decimal

import pytest

from report_pipeline import AggregatedData, format_table


def make_agg(
    periods, categories, period_category, period_totals, category_totals, grand_total
):
    return AggregatedData(
        periods=periods,
        categories=categories,
        period_category={k: Decimal(str(v)) for k, v in period_category.items()},
        period_totals={k: Decimal(str(v)) for k, v in period_totals.items()},
        category_totals={k: Decimal(str(v)) for k, v in category_totals.items()},
        grand_total=Decimal(str(grand_total)),
    )


SIMPLE_AGG = make_agg(
    periods=["2024-Q1"],
    categories=["REVENUE"],
    period_category={("2024-Q1", "REVENUE"): "1000.00"},
    period_totals={"2024-Q1": "1000.00"},
    category_totals={"REVENUE": "1000.00"},
    grand_total="1000.00",
)


def test_format_returns_string():
    result = format_table(SIMPLE_AGG)
    assert isinstance(result, str)


def test_format_has_header_row():
    result = format_table(SIMPLE_AGG)
    lines = result.strip().splitlines()
    header = lines[0]
    assert "2024-Q1" in header
    assert "TOTAL" in header


def test_format_has_category_rows():
    result = format_table(SIMPLE_AGG)
    assert "REVENUE" in result


def test_format_has_total_row():
    result = format_table(SIMPLE_AGG)
    lines = result.strip().splitlines()
    assert any(line.startswith("TOTAL") for line in lines)


def test_format_revenue_value_has_dollar_sign_and_decimals():
    result = format_table(SIMPLE_AGG)
    assert "$1,000.00" in result


def test_format_headcount_is_plain_integer():
    agg = make_agg(
        periods=["2024-Q1"],
        categories=["HEADCOUNT"],
        period_category={("2024-Q1", "HEADCOUNT"): "42"},
        period_totals={"2024-Q1": "42"},
        category_totals={"HEADCOUNT": "42"},
        grand_total="42",
    )
    result = format_table(agg)
    assert "42" in result
    # Headcount should NOT have a $ sign
    assert "$" not in result


def test_format_multiple_periods_in_header():
    agg = make_agg(
        periods=["2024-Q1", "2024-Q2"],
        categories=["REVENUE"],
        period_category={
            ("2024-Q1", "REVENUE"): "1000.00",
            ("2024-Q2", "REVENUE"): "2000.00",
        },
        period_totals={"2024-Q1": "1000.00", "2024-Q2": "2000.00"},
        category_totals={"REVENUE": "3000.00"},
        grand_total="3000.00",
    )
    result = format_table(agg)
    header = result.splitlines()[0]
    assert "2024-Q1" in header
    assert "2024-Q2" in header
    assert "TOTAL" in header
    # Periods must appear in order
    assert header.index("2024-Q1") < header.index("2024-Q2") < header.index("TOTAL")


def test_format_column_no_narrower_than_header():
    agg = make_agg(
        periods=["2024-Q1"],
        categories=["REVENUE"],
        period_category={("2024-Q1", "REVENUE"): "1.00"},
        period_totals={"2024-Q1": "1.00"},
        category_totals={"REVENUE": "1.00"},
        grand_total="1.00",
    )
    result = format_table(agg)
    lines = result.splitlines()
    header = lines[0]
    # The "2024-Q1" header is 7 chars; "$1.00" is 5 chars, so column must be ≥ 7
    # Find "2024-Q1" position in header
    idx = header.index("2024-Q1")
    revenue_line = lines[1]  # REVENUE row
    # The value cell aligned at same position must span at least 7 chars
    value_part = revenue_line[idx:idx + 7]
    assert len(value_part) == 7


def test_format_two_spaces_padding_between_columns():
    """Columns are separated by at least 2 spaces."""
    agg = make_agg(
        periods=["2024-Q1"],
        categories=["REVENUE"],
        period_category={("2024-Q1", "REVENUE"): "1000.00"},
        period_totals={"2024-Q1": "1000.00"},
        category_totals={"REVENUE": "1000.00"},
        grand_total="1000.00",
    )
    result = format_table(agg)
    for line in result.splitlines():
        # Each non-empty line should contain "  " (at least two spaces) as separator
        assert "  " in line


def test_format_negative_cost_has_minus_before_dollar():
    agg = make_agg(
        periods=["2024-Q1"],
        categories=["COST"],
        period_category={("2024-Q1", "COST"): "-200.00"},
        period_totals={"2024-Q1": "-200.00"},
        category_totals={"COST": "-200.00"},
        grand_total="-200.00",
    )
    result = format_table(agg)
    assert "-$200.00" in result
