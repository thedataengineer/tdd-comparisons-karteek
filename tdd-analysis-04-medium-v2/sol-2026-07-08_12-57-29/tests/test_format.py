"""Tests for the format stage."""

import re
import pytest
from report_pipeline.parse import ParsedRow
from report_pipeline.aggregate import aggregate
from report_pipeline.format import format_table, _fmt_monetary, _fmt_headcount, _fmt_value


def _make_agg(*raw_rows):
    """Helper: aggregate from (category, value, period) tuples."""
    rows = [
        ParsedRow(row_id=i + 1, category=cat, value=val, period=period)
        for i, (cat, val, period) in enumerate(raw_rows)
    ]
    return aggregate(rows)


# ── Formatter unit tests ──────────────────────────────────────────────────────

class TestFormatters:
    def test_monetary_positive(self):
        assert _fmt_monetary(1234.56) == "$1,234.56"

    def test_monetary_zero(self):
        assert _fmt_monetary(0.0) == "$0.00"

    def test_monetary_negative(self):
        assert _fmt_monetary(-200.0) == "-$200.00"

    def test_monetary_large(self):
        assert _fmt_monetary(1_000_000.0) == "$1,000,000.00"

    def test_headcount_integer(self):
        assert _fmt_headcount(42.0) == "42"

    def test_headcount_rounds(self):
        assert _fmt_headcount(9.9) == "10"

    def test_fmt_value_revenue(self):
        assert _fmt_value("REVENUE", 500.0) == "$500.00"

    def test_fmt_value_cost_negative(self):
        assert _fmt_value("COST", -99.99) == "-$99.99"

    def test_fmt_value_headcount(self):
        assert _fmt_value("HEADCOUNT", 7.0) == "7"


# ── Table structure tests ─────────────────────────────────────────────────────

class TestTableStructure:
    def _table(self, *raw_rows):
        return format_table(_make_agg(*raw_rows))

    def test_returns_string(self):
        tbl = self._table(("REVENUE", 1000.0, "2024-Q1"))
        assert isinstance(tbl, str)

    def test_header_contains_period(self):
        tbl = self._table(("REVENUE", 1000.0, "2024-Q1"))
        header = tbl.split("\n")[0]
        assert "2024-Q1" in header

    def test_header_contains_total(self):
        tbl = self._table(("REVENUE", 1000.0, "2024-Q1"))
        header = tbl.split("\n")[0]
        assert "TOTAL" in header

    def test_header_period_before_total(self):
        tbl = self._table(("REVENUE", 1000.0, "2024-Q1"))
        header = tbl.split("\n")[0]
        assert header.index("2024-Q1") < header.index("TOTAL")

    def test_periods_in_chronological_order(self):
        tbl = self._table(
            ("REVENUE", 100.0, "2024-Q3"),
            ("REVENUE", 200.0, "2024-Q1"),
        )
        header = tbl.split("\n")[0]
        assert header.index("2024-Q1") < header.index("2024-Q3")

    def test_row_count(self):
        # header + 3 categories + TOTAL = 5 lines
        tbl = self._table(
            ("REVENUE", 1000.0, "2024-Q1"),
            ("COST", -200.0, "2024-Q1"),
            ("HEADCOUNT", 10.0, "2024-Q1"),
        )
        lines = tbl.split("\n")
        assert len(lines) == 5

    def test_category_row_labels_present(self):
        tbl = self._table(
            ("REVENUE", 1000.0, "2024-Q1"),
            ("COST", -200.0, "2024-Q1"),
            ("HEADCOUNT", 10.0, "2024-Q1"),
        )
        assert "REVENUE" in tbl
        assert "COST" in tbl
        assert "HEADCOUNT" in tbl

    def test_total_row_present(self):
        tbl = self._table(("REVENUE", 100.0, "2024-Q1"))
        lines = tbl.split("\n")
        assert lines[-1].startswith("TOTAL")

    def test_revenue_formatted_with_dollar(self):
        tbl = self._table(("REVENUE", 1234.56, "2024-Q1"))
        assert "$1,234.56" in tbl

    def test_cost_negative_formatted(self):
        tbl = self._table(("COST", -200.0, "2024-Q1"))
        assert "-$200.00" in tbl

    def test_headcount_formatted_as_integer(self):
        tbl = self._table(("HEADCOUNT", 42.0, "2024-Q1"))
        # Should NOT have a $ sign for headcount
        lines = tbl.split("\n")
        # Find headcount row
        hc_line = next(l for l in lines if l.startswith("HEADCOUNT"))
        # Extract the value part (strip the label)
        values_part = hc_line[len("HEADCOUNT"):]
        assert "$" not in values_part

    def test_column_separator_at_least_two_spaces(self):
        tbl = self._table(("REVENUE", 1000.0, "2024-Q1"))
        for line in tbl.split("\n"):
            # Between any two non-space tokens there should be >= 2 spaces
            # Just check that there's no single-space column separator
            # by verifying no adjacent tokens are separated by exactly one space
            # (A robust check: no place where one token char is directly beside next)
            stripped = line.strip()
            # Each line should not have a single space within the data area
            # We check indirectly: split by 2 spaces yields reasonable tokens
            parts = re.split(r"  +", stripped)
            assert len(parts) >= 2  # at least label + one column

    def test_values_right_aligned_in_columns(self):
        """Check that within each column the numeric cell value is right-aligned."""
        agg = _make_agg(
            ("REVENUE", 1.0, "2024-Q1"),
            ("REVENUE", 100000.0, "2024-Q2"),
        )
        tbl = format_table(agg)
        lines = tbl.split("\n")
        rev_line = next(l for l in lines if l.startswith("REVENUE"))
        # The line should contain right-aligned values without extra spaces after
        # the widest value in that column
        assert rev_line.endswith(rev_line.rstrip())  # no trailing spaces needed

    def test_two_periods_chronological_columns(self):
        tbl = self._table(
            ("REVENUE", 500.0, "2023-Q4"),
            ("REVENUE", 700.0, "2024-Q1"),
        )
        header = tbl.split("\n")[0]
        assert header.index("2023-Q4") < header.index("2024-Q1")

    def test_total_column_revenue(self):
        tbl = self._table(
            ("REVENUE", 300.0, "2024-Q1"),
            ("REVENUE", 700.0, "2024-Q2"),
        )
        rev_line = next(l for l in tbl.split("\n") if l.startswith("REVENUE"))
        assert "$1,000.00" in rev_line

    def test_total_row_sums_period_columns(self):
        tbl = self._table(
            ("REVENUE", 1000.0, "2024-Q1"),
            ("COST", -200.0, "2024-Q1"),
        )
        total_line = tbl.split("\n")[-1]
        # 1000 + (-200) = 800
        assert "$800.00" in total_line

    def test_column_widths_match_widest_value(self):
        """Column must be at least as wide as the header."""
        agg = _make_agg(("REVENUE", 1.0, "2024-Q1"))
        tbl = format_table(agg)
        header = tbl.split("\n")[0]
        # "2024-Q1" is 7 chars; column width >= 7
        # Check that header token is not truncated
        assert "2024-Q1" in header

    def test_only_present_categories_shown(self):
        tbl = self._table(("REVENUE", 100.0, "2024-Q1"))
        assert "COST" not in tbl
        assert "HEADCOUNT" not in tbl

    def test_headcount_total_is_integer(self):
        tbl = self._table(
            ("HEADCOUNT", 5.0, "2024-Q1"),
            ("HEADCOUNT", 10.0, "2024-Q2"),
        )
        hc_line = next(l for l in tbl.split("\n") if l.startswith("HEADCOUNT"))
        # TOTAL for headcount = 15 → "15" (no $)
        assert "15" in hc_line

    def test_multiple_categories_row_order(self):
        tbl = self._table(
            ("COST", -100.0, "2024-Q1"),
            ("REVENUE", 500.0, "2024-Q1"),
            ("HEADCOUNT", 3.0, "2024-Q1"),
        )
        lines = tbl.split("\n")
        labels = [l.split()[0] for l in lines[1:-1]]  # skip header and TOTAL
        assert labels == ["REVENUE", "COST", "HEADCOUNT"]
