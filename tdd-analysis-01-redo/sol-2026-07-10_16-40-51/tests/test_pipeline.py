import pytest
from report_pipeline.pipeline import parse, aggregate, format_table, validate_output, run_pipeline


# ─── Stage 1: Parse ───────────────────────────────────────────────────────────

def test_parse_single_valid_row():
    rows = parse(["1:REVENUE:1000.00:2024-Q1"])
    assert rows == [{"row_id": 1, "category": "REVENUE", "value": 1000.00, "period": "2024-Q1"}]


def test_parse_multiple_rows():
    rows = parse([
        "1:REVENUE:1000.00:2024-Q1",
        "2:COST:-200.00:2024-Q1",
        "3:HEADCOUNT:5:2024-Q2",
    ])
    assert len(rows) == 3
    assert rows[0] == {"row_id": 1, "category": "REVENUE", "value": 1000.00, "period": "2024-Q1"}
    assert rows[1] == {"row_id": 2, "category": "COST", "value": -200.00, "period": "2024-Q1"}
    assert rows[2] == {"row_id": 3, "category": "HEADCOUNT", "value": 5.0, "period": "2024-Q2"}


def test_parse_error_negative_revenue():
    result = parse(["1:REVENUE:-500.00:2024-Q1"])
    assert result == {"error": "parse", "input": "1:REVENUE:-500.00:2024-Q1", "reason": "REVENUE value cannot be negative"}


def test_parse_error_negative_headcount():
    result = parse(["1:HEADCOUNT:-3:2024-Q1"])
    assert result == {"error": "parse", "input": "1:HEADCOUNT:-3:2024-Q1", "reason": "HEADCOUNT value cannot be negative"}


def test_parse_error_invalid_period():
    result = parse(["1:REVENUE:100.00:2024-Q5"])
    assert result == {"error": "parse", "input": "1:REVENUE:100.00:2024-Q5", "reason": "invalid period format"}


def test_parse_error_invalid_category():
    result = parse(["1:PROFIT:100.00:2024-Q1"])
    assert result == {"error": "parse", "input": "1:PROFIT:100.00:2024-Q1", "reason": "invalid category"}


def test_parse_error_reports_failing_row():
    # second row is invalid; error should identify that row
    result = parse([
        "1:REVENUE:100.00:2024-Q1",
        "2:COST:-50.00:2024-Q1",
        "3:HEADCOUNT:-1:2024-Q1",
    ])
    assert result == {"error": "parse", "input": "3:HEADCOUNT:-1:2024-Q1", "reason": "HEADCOUNT value cannot be negative"}


# ─── Stage 2: Aggregate ──────────────────────────────────────────────────────

def test_aggregate_single_period_single_category():
    parsed = [
        {"row_id": 1, "category": "REVENUE", "value": 1000.0, "period": "2024-Q1"},
        {"row_id": 2, "category": "REVENUE", "value": 500.0, "period": "2024-Q1"},
    ]
    result = aggregate(parsed)
    assert result["cells"]["2024-Q1"]["REVENUE"] == 1500.0


def test_aggregate_periods_sorted_chronologically():
    parsed = [
        {"row_id": 1, "category": "REVENUE", "value": 100.0, "period": "2024-Q3"},
        {"row_id": 2, "category": "REVENUE", "value": 200.0, "period": "2023-Q4"},
        {"row_id": 3, "category": "REVENUE", "value": 300.0, "period": "2024-Q1"},
    ]
    result = aggregate(parsed)
    assert result["periods"] == ["2023-Q4", "2024-Q1", "2024-Q3"]


def test_aggregate_period_totals():
    parsed = [
        {"row_id": 1, "category": "REVENUE", "value": 1000.0, "period": "2024-Q1"},
        {"row_id": 2, "category": "COST", "value": -200.0, "period": "2024-Q1"},
        {"row_id": 3, "category": "HEADCOUNT", "value": 5.0, "period": "2024-Q1"},
    ]
    result = aggregate(parsed)
    assert result["period_totals"]["2024-Q1"] == pytest.approx(805.0)


def test_aggregate_category_totals():
    parsed = [
        {"row_id": 1, "category": "REVENUE", "value": 1000.0, "period": "2024-Q1"},
        {"row_id": 2, "category": "REVENUE", "value": 2000.0, "period": "2024-Q2"},
        {"row_id": 3, "category": "COST", "value": -300.0, "period": "2024-Q1"},
    ]
    result = aggregate(parsed)
    assert result["category_totals"]["REVENUE"] == pytest.approx(3000.0)
    assert result["category_totals"]["COST"] == pytest.approx(-300.0)
    assert result["category_totals"]["HEADCOUNT"] == pytest.approx(0.0)


# ─── Stage 3: Format ─────────────────────────────────────────────────────────

def _simple_aggregated():
    """Helper: aggregated data for a single period, all 3 categories."""
    return aggregate([
        {"row_id": 1, "category": "REVENUE", "value": 1000.0, "period": "2024-Q1"},
        {"row_id": 2, "category": "COST", "value": -200.0, "period": "2024-Q1"},
        {"row_id": 3, "category": "HEADCOUNT", "value": 5.0, "period": "2024-Q1"},
    ])


def test_format_returns_string():
    result = format_table(_simple_aggregated())
    assert isinstance(result, str)


def test_format_header_contains_period_and_total():
    result = format_table(_simple_aggregated())
    header = result.splitlines()[0]
    assert "2024-Q1" in header
    assert "TOTAL" in header


# ─── Stage 4: Validate Output ────────────────────────────────────────────────

def test_validate_passes_on_valid_table():
    agg = _simple_aggregated()
    table = format_table(agg)
    result = validate_output(table, agg)
    assert result == table


def test_validate_error_missing_period():
    agg = _simple_aggregated()
    # tamper with the table to drop the period column reference
    table = format_table(agg).replace("2024-Q1", "XXXX-XX")
    result = validate_output(table, agg)
    assert isinstance(result, dict)
    assert result["error"] == "validate"
    assert "2024-Q1" in result["reason"]


def test_validate_error_wrong_total():
    agg = _simple_aggregated()
    # tamper: replace the known TOTAL value with a wrong one
    table = format_table(agg).replace("$1,000.00", "$9,999.99")
    result = validate_output(table, agg)
    assert isinstance(result, dict)
    assert result["error"] == "validate"


# ─── Full Pipeline ─────────────────────────────────────────────────────────────

def test_run_pipeline_success():
    raw = [
        "1:REVENUE:1000.00:2024-Q1",
        "2:COST:-200.00:2024-Q1",
        "3:HEADCOUNT:5:2024-Q1",
    ]
    result = run_pipeline(raw)
    assert isinstance(result, str)
    assert "REVENUE" in result
    assert "2024-Q1" in result


def test_run_pipeline_parse_error_propagated():
    result = run_pipeline(["1:REVENUE:-100.00:2024-Q1"])
    assert isinstance(result, dict)
    assert result["error"] == "parse"


def test_validate_error_column_narrower_than_header():
    agg = _simple_aggregated()
    # Construct a table where a data line is shorter than the header
    table = format_table(agg)
    lines = table.splitlines()
    # Truncate a data line to be shorter than the header
    lines[1] = lines[1][:5]  # very short
    tampered = "\n".join(lines)
    result = validate_output(tampered, agg)
    assert isinstance(result, dict)
    assert result["error"] == "validate"

def test_format_revenue_dollar_format():
    agg = aggregate([
        {"row_id": 1, "category": "REVENUE", "value": 1234567.89, "period": "2024-Q1"},
    ])
    result = format_table(agg)
    assert "$1,234,567.89" in result


def test_format_negative_cost_format():
    agg = aggregate([
        {"row_id": 1, "category": "COST", "value": -200.0, "period": "2024-Q1"},
    ])
    result = format_table(agg)
    assert "-$200.00" in result


def test_format_headcount_plain_integer():
    agg = aggregate([
        {"row_id": 1, "category": "HEADCOUNT", "value": 42.0, "period": "2024-Q1"},
    ])
    result = format_table(agg)
    lines = result.splitlines()
    headcount_line = next(l for l in lines if l.startswith("HEADCOUNT"))
    assert "42" in headcount_line
    assert "$" not in headcount_line


def test_format_total_row_last_line():
    result = format_table(_simple_aggregated())
    last_line = result.splitlines()[-1]
    assert last_line.startswith("TOTAL")


def test_format_row_count():
    # header + 3 category rows + TOTAL row = 5 lines
    result = format_table(_simple_aggregated())
    assert len(result.splitlines()) == 5


def test_format_multiple_periods_column_count():
    agg = aggregate([
        {"row_id": 1, "category": "REVENUE", "value": 100.0, "period": "2024-Q1"},
        {"row_id": 2, "category": "REVENUE", "value": 200.0, "period": "2024-Q2"},
    ])
    result = format_table(agg)
    header = result.splitlines()[0]
    assert "2024-Q1" in header
    assert "2024-Q2" in header
    assert "TOTAL" in header
