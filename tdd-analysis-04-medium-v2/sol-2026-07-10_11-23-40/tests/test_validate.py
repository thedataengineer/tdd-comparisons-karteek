"""Tests for the validate_output stage."""
from decimal import Decimal

import pytest

from report_pipeline import AggregatedData, ValidationError, format_table, validate_output


def make_agg(periods, categories, period_category, period_totals, category_totals, grand_total):
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


def test_validate_valid_table_returns_string():
    table = format_table(SIMPLE_AGG)
    result = validate_output(table, SIMPLE_AGG)
    assert isinstance(result, str)
    assert result == table


def test_validate_mismatched_category_total_returns_error():
    """If category_totals don't match sum of period values, return ValidationError."""
    agg = make_agg(
        periods=["2024-Q1"],
        categories=["REVENUE"],
        period_category={("2024-Q1", "REVENUE"): "1000.00"},
        period_totals={"2024-Q1": "1000.00"},
        category_totals={"REVENUE": "9999.00"},  # wrong!
        grand_total="9999.00",
    )
    table = format_table(agg)
    result = validate_output(table, agg)
    assert isinstance(result, ValidationError)
    assert "REVENUE" in result.reason or "TOTAL" in result.reason


def test_validate_mismatched_grand_total_returns_error():
    """If grand_total doesn't match sum of period_totals, return ValidationError."""
    agg = make_agg(
        periods=["2024-Q1"],
        categories=["REVENUE"],
        period_category={("2024-Q1", "REVENUE"): "1000.00"},
        period_totals={"2024-Q1": "1000.00"},
        category_totals={"REVENUE": "1000.00"},
        grand_total="5000.00",  # wrong!
    )
    table = format_table(agg)
    result = validate_output(table, agg)
    assert isinstance(result, ValidationError)


def test_validate_empty_table_string_returns_error():
    result = validate_output("", SIMPLE_AGG)
    assert isinstance(result, ValidationError)
    assert "empty" in result.reason.lower() or "period" in result.reason.lower()


def test_validate_empty_table_no_periods_returns_error():
    """Table is empty string and aggregated has no periods — triggers 'table is empty' branch."""
    from report_pipeline import AggregatedData
    from decimal import Decimal
    agg_no_periods = AggregatedData(
        periods=[],
        categories=[],
        period_category={},
        period_totals={},
        category_totals={},
        grand_total=Decimal(0),
    )
    result = validate_output("", agg_no_periods)
    assert isinstance(result, ValidationError)
    assert "empty" in result.reason.lower()


def test_validate_period_in_body_but_not_header():
    """Period appears in table body but not in header line."""
    # "2024-Q1" is in table_str (passes first check), but not in header line
    bad_table = "         TOTAL\nREVENUE 2024-Q1 $1,000.00  $1,000.00"
    result = validate_output(bad_table, SIMPLE_AGG)
    assert isinstance(result, ValidationError)
    assert "2024-Q1" in result.reason or "header" in result.reason.lower()


def test_validate_missing_total_column_returns_error():
    bad_table = "           2024-Q1\nREVENUE    $1,000.00\n"
    result = validate_output(bad_table, SIMPLE_AGG)
    assert isinstance(result, ValidationError)


def test_validate_missing_period_returns_validation_error():
    """If a period from aggregated data is not in the table, return ValidationError."""
    agg = make_agg(
        periods=["2024-Q1", "2024-Q2"],
        categories=["REVENUE"],
        period_category={
            ("2024-Q1", "REVENUE"): "500",
            ("2024-Q2", "REVENUE"): "300",
        },
        period_totals={"2024-Q1": "500", "2024-Q2": "300"},
        category_totals={"REVENUE": "800"},
        grand_total="800",
    )
    # Provide a table missing the 2024-Q2 column
    bad_table = "           2024-Q1     TOTAL\nREVENUE    $500.00   $500.00\nTOTAL      $500.00   $500.00"
    result = validate_output(bad_table, agg)
    assert isinstance(result, ValidationError)
    assert result.stage == "validate"
    assert "2024-Q2" in result.reason or "period" in result.reason.lower()
