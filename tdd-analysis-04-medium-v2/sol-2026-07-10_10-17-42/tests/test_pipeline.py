"""Tests for the full run_pipeline function."""

import report_pipeline
from report_pipeline.models import PipelineError, ParseError, FormatError
from report_pipeline.pipeline import run_pipeline


def test_public_api_exports_all_stages():
    """All required callables are accessible from the top-level package."""
    assert callable(report_pipeline.parse)
    assert callable(report_pipeline.aggregate)
    assert callable(report_pipeline.format_table)
    assert callable(report_pipeline.validate_output)
    assert callable(report_pipeline.run_pipeline)



VALID_ROWS = [
    "1:REVENUE:1000.00:2024-Q1",
    "2:COST:-200.00:2024-Q1",
    "3:HEADCOUNT:10:2024-Q1",
]


def test_run_pipeline_returns_string_for_valid_input():
    result = run_pipeline(VALID_ROWS)
    assert isinstance(result, str)


def test_run_pipeline_table_contains_expected_values():
    result = run_pipeline(VALID_ROWS)
    assert isinstance(result, str)
    assert "REVENUE" in result
    assert "$1,000.00" in result
    assert "2024-Q1" in result


def test_run_pipeline_returns_pipeline_error_on_parse_failure():
    result = run_pipeline(["1:BADCAT:100.00:2024-Q1"])
    assert isinstance(result, PipelineError)
    assert result.stage == "parse"
    assert isinstance(result.error, ParseError)


def test_run_pipeline_pipeline_error_preserves_input_string():
    result = run_pipeline(["1:REVENUE:-500:2024-Q1"])  # negative REVENUE
    assert isinstance(result, PipelineError)
    assert result.error.input_string == "1:REVENUE:-500:2024-Q1"


def test_run_pipeline_multi_period_full_integration():
    """End-to-end: multiple periods and categories produce a correct table."""
    rows = [
        "1:REVENUE:1000.00:2024-Q1",
        "2:REVENUE:2000.00:2024-Q2",
        "3:COST:-300.00:2024-Q1",
        "4:COST:-400.00:2024-Q2",
        "5:HEADCOUNT:10:2024-Q1",
        "6:HEADCOUNT:12:2024-Q2",
    ]
    result = run_pipeline(rows)
    assert isinstance(result, str)
    lines = result.splitlines()
    # Header has both periods
    assert "2024-Q1" in lines[0]
    assert "2024-Q2" in lines[0]
    assert "TOTAL" in lines[0]
    # 2024-Q1 before 2024-Q2
    assert lines[0].index("2024-Q1") < lines[0].index("2024-Q2")
    # Revenue total across both periods
    revenue_line = next(l for l in lines if l.startswith("REVENUE"))
    assert "$3,000.00" in revenue_line
    # TOTAL row grand total: (1000-300+10) + (2000-400+12) = 710 + 1612 = 2322
    total_line = next(l for l in lines if l.startswith("TOTAL"))
    assert "$2,322.00" in total_line


def test_run_pipeline_returns_pipeline_error_on_format_failure(monkeypatch):
    """If format_table returns a FormatError, pipeline wraps it as PipelineError."""
    from report_pipeline import pipeline as pipeline_module
    from report_pipeline.models import FormatError

    def fake_format_table(agg):
        return FormatError(reason="simulated format error")

    monkeypatch.setattr(pipeline_module, "format_table", fake_format_table)
    result = run_pipeline(VALID_ROWS)
    assert isinstance(result, PipelineError)
    assert result.stage == "format"
    assert isinstance(result.error, FormatError)
    assert result.error.reason == "simulated format error"
