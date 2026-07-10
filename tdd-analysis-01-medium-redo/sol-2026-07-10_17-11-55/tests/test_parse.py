"""Tests for the parse stage of the report pipeline."""
from decimal import Decimal
import pytest
from report_pipeline.parse import parse


class TestParseValidInputs:
    def test_single_revenue_row(self):
        rows = parse(["1:REVENUE:1000.00:2024-Q1"])
        assert rows == [{"row_id": 1, "category": "REVENUE", "value": Decimal("1000.00"), "period": "2024-Q1"}]

    def test_single_cost_row(self):
        rows = parse(["2:COST:-200.50:2024-Q1"])
        assert rows == [{"row_id": 2, "category": "COST", "value": Decimal("-200.50"), "period": "2024-Q1"}]

    def test_cost_row_positive_value(self):
        rows = parse(["3:COST:500.00:2024-Q2"])
        assert rows == [{"row_id": 3, "category": "COST", "value": Decimal("500.00"), "period": "2024-Q2"}]

    def test_single_headcount_row(self):
        rows = parse(["4:HEADCOUNT:10:2024-Q1"])
        assert rows == [{"row_id": 4, "category": "HEADCOUNT", "value": Decimal("10"), "period": "2024-Q1"}]

    def test_multiple_rows(self):
        rows = parse([
            "1:REVENUE:5000.00:2024-Q1",
            "2:COST:-1000.00:2024-Q1",
            "3:HEADCOUNT:50:2024-Q1",
        ])
        assert len(rows) == 3
        assert rows[0]["category"] == "REVENUE"
        assert rows[1]["category"] == "COST"
        assert rows[2]["category"] == "HEADCOUNT"

    def test_all_quarters(self):
        inputs = [
            f"{i+1}:REVENUE:100:2024-Q{i+1}" for i in range(4)
        ]
        rows = parse(inputs)
        assert len(rows) == 4
        periods = [r["period"] for r in rows]
        assert periods == ["2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4"]

    def test_multiple_periods(self):
        rows = parse([
            "1:REVENUE:1000:2023-Q4",
            "2:REVENUE:2000:2024-Q1",
        ])
        assert rows[0]["period"] == "2023-Q4"
        assert rows[1]["period"] == "2024-Q1"

    def test_empty_input(self):
        rows = parse([])
        assert rows == []

    def test_integer_value(self):
        rows = parse(["1:REVENUE:1000:2024-Q1"])
        assert rows[0]["value"] == Decimal("1000")

    def test_row_id_is_integer(self):
        rows = parse(["42:REVENUE:100:2024-Q1"])
        assert rows[0]["row_id"] == 42
        assert isinstance(rows[0]["row_id"], int)

    def test_zero_value_revenue(self):
        rows = parse(["1:REVENUE:0.00:2024-Q1"])
        assert rows[0]["value"] == Decimal("0.00")

    def test_zero_value_headcount(self):
        rows = parse(["1:HEADCOUNT:0:2024-Q1"])
        assert rows[0]["value"] == Decimal("0")


class TestParseErrors:
    def _assert_error(self, result, expected_input=None, reason_contains=None):
        assert isinstance(result, dict)
        assert result.get("stage") == "parse"
        assert "input" in result
        assert "reason" in result
        if expected_input is not None:
            assert result["input"] == expected_input
        if reason_contains is not None:
            assert reason_contains.lower() in result["reason"].lower()

    def test_too_few_fields(self):
        result = parse(["1:REVENUE:1000"])
        self._assert_error(result, "1:REVENUE:1000")

    def test_too_many_fields(self):
        result = parse(["1:REVENUE:1000:2024-Q1:extra"])
        self._assert_error(result, "1:REVENUE:1000:2024-Q1:extra")

    def test_invalid_row_id_zero(self):
        result = parse(["0:REVENUE:1000:2024-Q1"])
        self._assert_error(result, "0:REVENUE:1000:2024-Q1")

    def test_invalid_row_id_negative(self):
        result = parse(["-1:REVENUE:1000:2024-Q1"])
        self._assert_error(result, "-1:REVENUE:1000:2024-Q1")

    def test_invalid_row_id_non_integer(self):
        result = parse(["abc:REVENUE:1000:2024-Q1"])
        self._assert_error(result, "abc:REVENUE:1000:2024-Q1")

    def test_invalid_category(self):
        result = parse(["1:PROFIT:1000:2024-Q1"])
        self._assert_error(result, "1:PROFIT:1000:2024-Q1", "category")

    def test_invalid_value_non_numeric(self):
        result = parse(["1:REVENUE:abc:2024-Q1"])
        self._assert_error(result, "1:REVENUE:abc:2024-Q1", "value")

    def test_negative_revenue_is_error(self):
        result = parse(["1:REVENUE:-100:2024-Q1"])
        self._assert_error(result, "1:REVENUE:-100:2024-Q1")

    def test_negative_headcount_is_error(self):
        result = parse(["1:HEADCOUNT:-5:2024-Q1"])
        self._assert_error(result, "1:HEADCOUNT:-5:2024-Q1")

    def test_invalid_period_format(self):
        result = parse(["1:REVENUE:1000:2024-Q5"])
        self._assert_error(result, "1:REVENUE:1000:2024-Q5", "period")

    def test_invalid_period_no_quarter(self):
        result = parse(["1:REVENUE:1000:2024"])
        self._assert_error(result, "1:REVENUE:1000:2024", "period")

    def test_invalid_period_wrong_format(self):
        result = parse(["1:REVENUE:1000:Q1-2024"])
        self._assert_error(result, "1:REVENUE:1000:Q1-2024", "period")

    def test_invalid_period_q0(self):
        result = parse(["1:REVENUE:1000:2024-Q0"])
        self._assert_error(result, "1:REVENUE:1000:2024-Q0", "period")

    def test_duplicate_row_id(self):
        result = parse(["1:REVENUE:1000:2024-Q1", "1:COST:500:2024-Q1"])
        self._assert_error(result)

    def test_returns_first_failing_row(self):
        result = parse([
            "1:REVENUE:1000:2024-Q1",
            "2:INVALID:500:2024-Q1",
            "3:HEADCOUNT:10:2024-Q1",
        ])
        self._assert_error(result, "2:INVALID:500:2024-Q1", "category")
