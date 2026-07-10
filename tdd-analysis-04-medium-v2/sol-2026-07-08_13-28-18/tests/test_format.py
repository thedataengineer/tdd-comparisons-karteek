"""Tests for the format stage."""

import pytest
from decimal import Decimal

from report_pipeline.parse import ParsedRow
from report_pipeline.aggregate import aggregate
from report_pipeline.format import format_table, _format_value


def make_row(row_id, category, value, period):
    return ParsedRow(row_id=row_id, category=category, value=Decimal(str(value)), period=period)


def make_table(*lines):
    """Parse raw strings through aggregate then format."""
    from report_pipeline.parse import parse
    rows = parse(list(lines))
    data = aggregate(rows)
    return format_table(data)


# ---------- _format_value unit tests ----------

def test_format_value_revenue():
    assert _format_value("REVENUE", Decimal("1234.56")) == "$1,234.56"


def test_format_value_revenue_thousands():
    assert _format_value("REVENUE", Decimal("1000000")) == "$1,000,000.00"


def test_format_value_cost_negative():
    assert _format_value("COST", Decimal("-200")) == "-$200.00"


def test_format_value_cost_positive():
    assert _format_value("COST", Decimal("300")) == "$300.00"


def test_format_value_headcount():
    assert _format_value("HEADCOUNT", Decimal("42")) == "42"


def test_format_value_headcount_zero():
    assert _format_value("HEADCOUNT", Decimal("0")) == "0"


# ---------- Table structure tests ----------

def test_format_table_has_header():
    table = make_table("1:REVENUE:1000:2024-Q1")
    lines = table.splitlines()
    assert "2024-Q1" in lines[0]
    assert "TOTAL" in lines[0]


def test_format_table_category_row_present():
    table = make_table("1:REVENUE:1000:2024-Q1")
    assert "REVENUE" in table


def test_format_table_total_row_present():
    table = make_table("1:REVENUE:1000:2024-Q1")
    lines = table.splitlines()
    assert any(line.strip().startswith("TOTAL") for line in lines)


def test_format_table_period_order():
    table = make_table(
        "1:REVENUE:1000:2024-Q3",
        "2:REVENUE:2000:2024-Q1",
    )
    header = table.splitlines()[0]
    idx_q1 = header.index("2024-Q1")
    idx_q3 = header.index("2024-Q3")
    assert idx_q1 < idx_q3


def test_format_table_values_right_aligned():
    table = make_table("1:REVENUE:1000:2024-Q1")
    lines = table.splitlines()
    # All data rows: the value should be right-aligned (no trailing spaces)
    for line in lines[1:]:
        assert not line.endswith(" ")


def test_format_table_negative_cost():
    table = make_table(
        "1:REVENUE:1000:2024-Q1",
        "2:COST:-200:2024-Q1",
    )
    assert "-$200.00" in table


def test_format_table_headcount_plain_integer():
    table = make_table("1:HEADCOUNT:42:2024-Q1")
    assert "42" in table
    # Should not have $ for headcount
    lines = table.splitlines()
    headcount_line = next(l for l in lines if "HEADCOUNT" in l)
    # strip label, check no $ in value
    rest = headcount_line[len("HEADCOUNT"):]
    assert "$" not in rest


def test_format_table_multiple_periods():
    table = make_table(
        "1:REVENUE:1000:2024-Q1",
        "2:REVENUE:2000:2024-Q2",
    )
    assert "2024-Q1" in table
    assert "2024-Q2" in table


def test_format_table_multi_category_multi_period():
    lines_in = [
        "1:REVENUE:10000:2024-Q1",
        "2:COST:-2000:2024-Q1",
        "3:HEADCOUNT:5:2024-Q1",
        "4:REVENUE:12000:2024-Q2",
        "5:COST:-3000:2024-Q2",
        "6:HEADCOUNT:6:2024-Q2",
    ]
    table = make_table(*lines_in)
    lines = table.splitlines()
    # Should have: header, REVENUE, COST, HEADCOUNT, TOTAL = 5 lines
    assert len(lines) == 5
    assert "REVENUE" in lines[1]
    assert "COST" in lines[2]
    assert "HEADCOUNT" in lines[3]
    assert "TOTAL" in lines[4]


def test_format_table_total_column_matches_sum():
    """The TOTAL column for each row must equal sum of its period values."""
    from report_pipeline.parse import parse
    from report_pipeline.aggregate import aggregate
    from report_pipeline.validate import validate_output

    lines_in = [
        "1:REVENUE:10000:2024-Q1",
        "2:REVENUE:20000:2024-Q2",
    ]
    rows = parse(lines_in)
    data = aggregate(rows)
    table = format_table(data)
    result = validate_output(table, data)
    assert result == table  # validation should pass


def test_format_all_headcount_totals_as_int():
    table = make_table(
        "1:HEADCOUNT:10:2024-Q1",
        "2:HEADCOUNT:20:2024-Q2",
    )
    lines = table.splitlines()
    total_line = lines[-1]
    # Should not have $ in TOTAL row for all-headcount
    assert "$" not in total_line


def test_format_column_widths_at_least_header_width():
    """Each column must be at least as wide as its header."""
    table = make_table("1:REVENUE:1:2024-Q1")
    lines = table.splitlines()
    header = lines[0]
    # Find TOTAL column position
    total_pos = header.index("TOTAL")
    # Check data rows: the TOTAL field starts at same position
    for line in lines[1:]:
        if len(line) > total_pos:
            field = line[total_pos:].split()[0]
            # This field should be at least 5 chars wide (TOTAL is 5) - right aligned
            # so the start position gives us the right-aligned value
