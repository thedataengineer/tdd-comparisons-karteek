"""Tests for the full pipeline."""
import pytest
from report_pipeline.pipeline import run_pipeline


class TestPipelineSuccess:
    def test_single_revenue_row(self):
        raw = ["1:REVENUE:1000.00:2024-Q1"]
        result = run_pipeline(raw)
        assert isinstance(result, str)
        assert "REVENUE" in result
        assert "$1,000.00" in result

    def test_full_example(self):
        raw = [
            "1:REVENUE:10000.00:2024-Q1",
            "2:REVENUE:20000.00:2024-Q2",
            "3:COST:-3000.00:2024-Q1",
            "4:COST:-4000.00:2024-Q2",
            "5:HEADCOUNT:100:2024-Q1",
            "6:HEADCOUNT:110:2024-Q2",
        ]
        result = run_pipeline(raw)
        assert isinstance(result, str)
        assert "REVENUE" in result
        assert "COST" in result
        assert "HEADCOUNT" in result
        assert "2024-Q1" in result
        assert "2024-Q2" in result
        assert "TOTAL" in result

    def test_periods_ordered(self):
        raw = [
            "1:REVENUE:1000.00:2024-Q2",
            "2:REVENUE:2000.00:2024-Q1",
        ]
        result = run_pipeline(raw)
        assert isinstance(result, str)
        q1_pos = result.find("2024-Q1")
        q2_pos = result.find("2024-Q2")
        assert q1_pos < q2_pos

    def test_negative_cost_in_output(self):
        raw = ["1:COST:-500.00:2024-Q1"]
        result = run_pipeline(raw)
        assert "-$500.00" in result

    def test_headcount_integer_in_output(self):
        raw = ["1:HEADCOUNT:25:2024-Q1"]
        result = run_pipeline(raw)
        assert "25" in result
        assert "$" not in result


class TestPipelineParseErrors:
    def _assert_error(self, result, stage=None):
        assert isinstance(result, dict)
        if stage:
            assert result.get("stage") == stage

    def test_invalid_category_returns_parse_error(self):
        raw = ["1:INVALID:1000:2024-Q1"]
        result = run_pipeline(raw)
        self._assert_error(result, "parse")

    def test_negative_revenue_returns_parse_error(self):
        raw = ["1:REVENUE:-100:2024-Q1"]
        result = run_pipeline(raw)
        self._assert_error(result, "parse")

    def test_invalid_period_returns_parse_error(self):
        raw = ["1:REVENUE:100:2024-Q5"]
        result = run_pipeline(raw)
        self._assert_error(result, "parse")

    def test_invalid_row_id_returns_parse_error(self):
        raw = ["0:REVENUE:100:2024-Q1"]
        result = run_pipeline(raw)
        self._assert_error(result, "parse")

    def test_duplicate_row_id_returns_parse_error(self):
        raw = ["1:REVENUE:100:2024-Q1", "1:COST:200:2024-Q1"]
        result = run_pipeline(raw)
        self._assert_error(result, "parse")


class TestPipelineEdgeCases:
    def test_empty_input_returns_empty_or_error(self):
        # Empty input could produce an empty table or an error
        # Either is acceptable; we just check it doesn't crash
        result = run_pipeline([])
        assert result is not None

    def test_single_period_all_categories(self):
        raw = [
            "1:REVENUE:5000.00:2024-Q1",
            "2:COST:-1000.00:2024-Q1",
            "3:HEADCOUNT:50:2024-Q1",
        ]
        result = run_pipeline(raw)
        assert isinstance(result, str)
        assert "$5,000.00" in result
        assert "-$1,000.00" in result
        assert "50" in result

    def test_multiple_rows_same_period_category_sums(self):
        raw = [
            "1:REVENUE:1000.00:2024-Q1",
            "2:REVENUE:2000.00:2024-Q1",
        ]
        result = run_pipeline(raw)
        assert isinstance(result, str)
        assert "$3,000.00" in result
