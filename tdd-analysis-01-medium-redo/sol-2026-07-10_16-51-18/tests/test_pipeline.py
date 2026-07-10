import pytest
from report_pipeline.parse import parse
from report_pipeline.aggregate import aggregate
from report_pipeline.format import format_table
from report_pipeline.validate import validate_output
from report_pipeline.pipeline import run_pipeline


# ─── Stage 1: Parse ───────────────────────────────────────────────────────────

def test_parse_single_valid_revenue_row():
    result = parse(["1:REVENUE:1000.00:2024-Q1"])
    assert result == [
        {"row_id": 1, "category": "REVENUE", "value": 1000.00, "period": "2024-Q1"}
    ]


def test_parse_multiple_rows():
    result = parse([
        "1:REVENUE:500.00:2024-Q1",
        "2:COST:-200.00:2024-Q1",
        "3:HEADCOUNT:10:2024-Q2",
    ])
    assert len(result) == 3
    assert result[1] == {"row_id": 2, "category": "COST", "value": -200.00, "period": "2024-Q1"}


def test_parse_negative_revenue_is_error():
    result = parse(["1:REVENUE:-500.00:2024-Q1"])
    assert result["error"] == "parse"
    assert result["input"] == "1:REVENUE:-500.00:2024-Q1"


def test_parse_negative_headcount_is_error():
    result = parse(["1:HEADCOUNT:-5:2024-Q1"])
    assert result["error"] == "parse"
    assert result["input"] == "1:HEADCOUNT:-5:2024-Q1"


def test_parse_invalid_period_format_is_error():
    result = parse(["1:REVENUE:100.00:2024-Q5"])
    assert result["error"] == "parse"
    assert result["input"] == "1:REVENUE:100.00:2024-Q5"


def test_parse_invalid_category_is_error():
    result = parse(["1:EXPENSES:100.00:2024-Q1"])
    assert result["error"] == "parse"
    assert result["input"] == "1:EXPENSES:100.00:2024-Q1"


def test_parse_error_identifies_failing_line():
    result = parse([
        "1:REVENUE:100.00:2024-Q1",
        "2:REVENUE:-50.00:2024-Q2",
    ])
    assert result["error"] == "parse"
    assert result["input"] == "2:REVENUE:-50.00:2024-Q2"


# ─── Stage 2: Aggregate ───────────────────────────────────────────────────────

def test_aggregate_single_row():
    rows = [
        {"row_id": 1, "category": "REVENUE", "value": 1000.00, "period": "2024-Q1"}
    ]
    result = aggregate(rows)
    assert result["by_period_category"]["2024-Q1"]["REVENUE"] == 1000.00


def test_aggregate_sums_same_period_category():
    rows = [
        {"row_id": 1, "category": "REVENUE", "value": 500.00, "period": "2024-Q1"},
        {"row_id": 2, "category": "REVENUE", "value": 300.00, "period": "2024-Q1"},
    ]
    result = aggregate(rows)
    assert result["by_period_category"]["2024-Q1"]["REVENUE"] == 800.00


def test_aggregate_period_subtotals():
    rows = [
        {"row_id": 1, "category": "REVENUE", "value": 1000.00, "period": "2024-Q1"},
        {"row_id": 2, "category": "COST", "value": -200.00, "period": "2024-Q1"},
    ]
    result = aggregate(rows)
    assert result["period_subtotals"]["2024-Q1"] == 800.00


def test_aggregate_category_grand_totals():
    rows = [
        {"row_id": 1, "category": "REVENUE", "value": 1000.00, "period": "2024-Q1"},
        {"row_id": 2, "category": "REVENUE", "value": 500.00, "period": "2024-Q2"},
    ]
    result = aggregate(rows)
    assert result["category_totals"]["REVENUE"] == 1500.00


def test_aggregate_periods_ordered_chronologically():
    rows = [
        {"row_id": 1, "category": "REVENUE", "value": 100.00, "period": "2024-Q3"},
        {"row_id": 2, "category": "REVENUE", "value": 200.00, "period": "2023-Q1"},
        {"row_id": 3, "category": "REVENUE", "value": 300.00, "period": "2024-Q1"},
    ]
    result = aggregate(rows)
    assert list(result["by_period_category"].keys()) == ["2023-Q1", "2024-Q1", "2024-Q3"]


# ─── Stage 3: Format ────────────────────────────────────────────────────

def _simple_agg():
    rows = [
        {"row_id": 1, "category": "REVENUE", "value": 1000.00, "period": "2024-Q1"},
    ]
    return aggregate(rows)


def test_format_returns_string():
    result = format_table(_simple_agg())
    assert isinstance(result, str)


def test_format_header_contains_period_and_total():
    result = format_table(_simple_agg())
    first_line = result.split("\n")[0]
    assert "2024-Q1" in first_line
    assert "TOTAL" in first_line


def test_format_revenue_dollar_prefix_and_decimals():
    result = format_table(_simple_agg())
    assert "$1,000.00" in result


def test_format_negative_cost_leading_minus():
    rows = [
        {"row_id": 1, "category": "COST", "value": -200.00, "period": "2024-Q1"},
    ]
    result = format_table(aggregate(rows))
    assert "-$200.00" in result


def test_format_headcount_plain_integer():
    rows = [
        {"row_id": 1, "category": "HEADCOUNT", "value": 42.0, "period": "2024-Q1"},
    ]
    result = format_table(aggregate(rows))
    lines = result.split("\n")
    hc_line = next(l for l in lines if l.startswith("HEADCOUNT"))
    assert "42" in hc_line
    assert "$" not in hc_line


def test_format_total_row_at_bottom():
    rows = [
        {"row_id": 1, "category": "REVENUE", "value": 1000.00, "period": "2024-Q1"},
        {"row_id": 2, "category": "COST", "value": -300.00, "period": "2024-Q1"},
    ]
    result = format_table(aggregate(rows))
    last_line = result.split("\n")[-1]
    assert last_line.startswith("TOTAL")
    assert "$700.00" in last_line


def test_format_column_widths_fit_headers():
    # "2024-Q1" is 7 chars; values might be shorter
    rows = [
        {"row_id": 1, "category": "HEADCOUNT", "value": 5, "period": "2024-Q1"},
    ]
    result = format_table(aggregate(rows))
    header = result.split("\n")[0]
    # "2024-Q1" must appear fully in the header
    assert "2024-Q1" in header
    # value column should be at least 7 chars wide (right-justified "5" padded to 7)
    hc_line = next(l for l in result.split("\n") if l.startswith("HEADCOUNT"))
    # the value "5" should appear right-aligned in a field of >=7 chars
    # at minimum the field contains 7 spaces for "2024-Q1"
    assert len(hc_line) >= len(header)


# ─── Stage 4: Validate Output ─────────────────────────────────────────────

def test_validate_output_valid_table_returns_same_string():
    rows = [
        {"row_id": 1, "category": "REVENUE", "value": 1000.00, "period": "2024-Q1"},
    ]
    agg = aggregate(rows)
    table = format_table(agg)
    result = validate_output(table, agg)
    assert result == table


def test_validate_detects_missing_period_column():
    rows = [
        {"row_id": 1, "category": "REVENUE", "value": 1000.00, "period": "2024-Q1"},
    ]
    agg = aggregate(rows)
    # Tamper with the table to remove the period
    table = format_table(agg).replace("2024-Q1", "XXXX-XX")
    result = validate_output(table, agg)
    assert result["error"] == "validate"


def test_validate_detects_missing_total_column_header():
    rows = [
        {"row_id": 1, "category": "REVENUE", "value": 1000.00, "period": "2024-Q1"},
    ]
    agg = aggregate(rows)
    # Replace TOTAL in header only
    lines = format_table(agg).split("\n")
    lines[0] = lines[0].replace("TOTAL", "XXXXX")
    table = "\n".join(lines)
    result = validate_output(table, agg)
    assert result["error"] == "validate"


def test_validate_detects_category_total_mismatch():
    rows = [
        {"row_id": 1, "category": "REVENUE", "value": 1000.00, "period": "2024-Q1"},
    ]
    agg = aggregate(rows)
    import copy
    bad_agg = copy.deepcopy(agg)
    bad_agg["by_period_category"]["2024-Q1"]["REVENUE"] = 9999.00
    table = format_table(aggregate(rows))  # correct table
    result = validate_output(table, bad_agg)
    assert result["error"] == "validate"


def test_validate_detects_period_total_mismatch_in_total_row():
    rows = [
        {"row_id": 1, "category": "REVENUE", "value": 1000.00, "period": "2024-Q1"},
    ]
    agg = aggregate(rows)
    import copy
    bad_agg = copy.deepcopy(agg)
    bad_agg["period_subtotals"]["2024-Q1"] = 9999.00
    table = format_table(aggregate(rows))  # correct table
    result = validate_output(table, bad_agg)
    assert result["error"] == "validate"


# ─── Full Pipeline ───────────────────────────────────────────────────────────

def test_run_pipeline_returns_string_for_valid_input():
    raw = ["1:REVENUE:1000.00:2024-Q1", "2:COST:-200.00:2024-Q1"]
    result = run_pipeline(raw)
    assert isinstance(result, str)
    assert "$1,000.00" in result


def test_run_pipeline_returns_parse_error_for_invalid_input():
    raw = ["1:REVENUE:-100.00:2024-Q1"]
    result = run_pipeline(raw)
    assert isinstance(result, dict)
    assert result["error"] == "parse"


def test_run_pipeline_full_multi_period_multi_category():
    raw = [
        "1:REVENUE:5000.00:2023-Q4",
        "2:COST:-1200.50:2023-Q4",
        "3:HEADCOUNT:25:2023-Q4",
        "4:REVENUE:6000.00:2024-Q1",
        "5:COST:-1500.00:2024-Q1",
        "6:HEADCOUNT:30:2024-Q1",
    ]
    result = run_pipeline(raw)
    assert isinstance(result, str)
    lines = result.split("\n")
    header = lines[0]
    assert "2023-Q4" in header
    assert "2024-Q1" in header
    assert "TOTAL" in header
    # Check revenue row totals: 5000 + 6000 = 11000
    rev_line = next(l for l in lines if l.startswith("REVENUE"))
    assert "$11,000.00" in rev_line
    # Check headcount row totals: 25 + 30 = 55
    hc_line = next(l for l in lines if l.startswith("HEADCOUNT"))
    assert "55" in hc_line


def test_run_pipeline_periods_in_header_match_input_periods():
    raw = ["1:REVENUE:100.00:2024-Q3", "2:REVENUE:200.00:2024-Q1"]
    result = run_pipeline(raw)
    assert isinstance(result, str)
    header = result.split("\n")[0]
    # Chronological order: 2024-Q1 before 2024-Q3
    idx_q1 = header.index("2024-Q1")
    idx_q3 = header.index("2024-Q3")
    assert idx_q1 < idx_q3


def test_validate_detects_wrong_total_column():
    rows = [
        {"row_id": 1, "category": "REVENUE", "value": 1000.00, "period": "2024-Q1"},
    ]
    agg = aggregate(rows)
    # Pass a tampered agg with wrong period subtotal to trigger mismatch
    import copy
    bad_agg = copy.deepcopy(agg)
    bad_agg["period_subtotals"]["2024-Q1"] = 9999.00
    table = format_table(agg)  # valid table
    result = validate_output(table, bad_agg)
    assert result["error"] == "validate"
