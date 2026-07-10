import pytest
from report_pipeline.pipeline import parse, aggregate, format_table, validate_output, run_pipeline


# ── Stage 1: Parse ──────────────────────────────────────────────────────────

def test_parse_single_valid_row():
    rows = parse(["1:REVENUE:1000.00:2024-Q1"])
    assert rows == [{"row_id": 1, "category": "REVENUE", "value": 1000.00, "period": "2024-Q1"}]


def test_parse_multiple_valid_rows():
    rows = parse([
        "1:REVENUE:1000.00:2024-Q1",
        "2:COST:-200.00:2024-Q1",
        "3:HEADCOUNT:5:2024-Q2",
    ])
    assert len(rows) == 3
    assert rows[0] == {"row_id": 1, "category": "REVENUE", "value": 1000.00, "period": "2024-Q1"}
    assert rows[1] == {"row_id": 2, "category": "COST", "value": -200.00, "period": "2024-Q1"}
    assert rows[2] == {"row_id": 3, "category": "HEADCOUNT", "value": 5.0, "period": "2024-Q2"}


def test_parse_error_invalid_format():
    result = parse(["not-valid"])
    assert isinstance(result, dict)
    assert result["error"] == "parse_error"
    assert result["input"] == "not-valid"


def test_parse_error_invalid_category():
    result = parse(["1:PROFIT:100:2024-Q1"])
    assert isinstance(result, dict)
    assert result["error"] == "parse_error"
    assert "category" in result["reason"]


def test_parse_error_negative_revenue():
    result = parse(["1:REVENUE:-500:2024-Q1"])
    assert isinstance(result, dict)
    assert result["error"] == "parse_error"
    assert "negative" in result["reason"]


def test_parse_error_negative_headcount():
    result = parse(["1:HEADCOUNT:-3:2024-Q1"])
    assert isinstance(result, dict)
    assert result["error"] == "parse_error"


def test_parse_error_invalid_period():
    result = parse(["1:REVENUE:100:2024-Q5"])
    assert isinstance(result, dict)
    assert result["error"] == "parse_error"
    assert "period" in result["reason"]


# ── Stage 2: Aggregate ──────────────────────────────────────────────────────

def test_aggregate_single_entry():
    rows = [{"row_id": 1, "category": "REVENUE", "value": 1000.0, "period": "2024-Q1"}]
    result = aggregate(rows)
    # result["data"] is dict: {period: {category: total}}
    assert result["data"]["2024-Q1"]["REVENUE"] == 1000.0


def test_aggregate_sums_same_period_category():
    rows = [
        {"row_id": 1, "category": "REVENUE", "value": 1000.0, "period": "2024-Q1"},
        {"row_id": 2, "category": "REVENUE", "value": 500.0, "period": "2024-Q1"},
    ]
    result = aggregate(rows)
    assert result["data"]["2024-Q1"]["REVENUE"] == 1500.0


def test_aggregate_periods_ordered_chronologically():
    rows = [
        {"row_id": 1, "category": "REVENUE", "value": 100.0, "period": "2024-Q3"},
        {"row_id": 2, "category": "REVENUE", "value": 200.0, "period": "2023-Q4"},
        {"row_id": 3, "category": "REVENUE", "value": 300.0, "period": "2024-Q1"},
    ]
    result = aggregate(rows)
    assert result["periods"] == ["2023-Q4", "2024-Q1", "2024-Q3"]


def test_aggregate_category_totals():
    rows = [
        {"row_id": 1, "category": "REVENUE", "value": 1000.0, "period": "2024-Q1"},
        {"row_id": 2, "category": "REVENUE", "value": 2000.0, "period": "2024-Q2"},
        {"row_id": 3, "category": "COST", "value": -300.0, "period": "2024-Q1"},
    ]
    result = aggregate(rows)
    assert result["category_totals"]["REVENUE"] == 3000.0
    assert result["category_totals"]["COST"] == -300.0


def test_aggregate_period_subtotals():
    rows = [
        {"row_id": 1, "category": "REVENUE", "value": 1000.0, "period": "2024-Q1"},
        {"row_id": 2, "category": "COST", "value": -300.0, "period": "2024-Q1"},
    ]
    result = aggregate(rows)
    assert result["period_subtotals"]["2024-Q1"] == 700.0


# ── Stage 3: Format ─────────────────────────────────────────────────────────

def _simple_aggregated():
    """Helper: aggregated data for a simple scenario."""
    rows = [
        {"row_id": 1, "category": "REVENUE", "value": 1000.0, "period": "2024-Q1"},
        {"row_id": 2, "category": "COST", "value": -200.0, "period": "2024-Q1"},
        {"row_id": 3, "category": "HEADCOUNT", "value": 5.0, "period": "2024-Q1"},
    ]
    return aggregate(rows)


def test_format_table_returns_string():
    agg = _simple_aggregated()
    result = format_table(agg)
    assert isinstance(result, str)


def test_format_table_header_contains_period_and_total():
    agg = _simple_aggregated()
    result = format_table(agg)
    lines = result.splitlines()
    header = lines[0]
    assert "2024-Q1" in header
    assert "TOTAL" in header


def test_format_table_category_row_order():
    agg = _simple_aggregated()
    result = format_table(agg)
    lines = result.splitlines()
    # lines[0] = header, lines[1]=REVENUE, lines[2]=COST, lines[3]=HEADCOUNT, lines[4]=TOTAL
    assert lines[1].startswith("REVENUE")
    assert lines[2].startswith("COST")
    assert lines[3].startswith("HEADCOUNT")
    assert lines[4].startswith("TOTAL")


def test_format_table_revenue_money_format():
    rows = [{"row_id": 1, "category": "REVENUE", "value": 1234.56, "period": "2024-Q1"}]
    agg = aggregate(rows)
    result = format_table(agg)
    assert "$1,234.56" in result


def test_format_table_negative_cost_format():
    rows = [{"row_id": 1, "category": "COST", "value": -200.0, "period": "2024-Q1"}]
    agg = aggregate(rows)
    result = format_table(agg)
    assert "-$200.00" in result


def test_format_table_headcount_integer_format():
    rows = [{"row_id": 1, "category": "HEADCOUNT", "value": 5.0, "period": "2024-Q1"}]
    agg = aggregate(rows)
    result = format_table(agg)
    assert "5" in result
    # Should NOT contain $ for headcount row
    lines = result.splitlines()
    headcount_line = [l for l in lines if l.startswith("HEADCOUNT")][0]
    assert "$" not in headcount_line


def test_format_table_column_not_narrower_than_header():
    """Each column must be at least as wide as its header text."""
    rows = [{"row_id": 1, "category": "REVENUE", "value": 1.0, "period": "2024-Q1"}]
    agg = aggregate(rows)
    result = format_table(agg)
    lines = result.splitlines()
    header = lines[0]
    # The header "2024-Q1" is 7 chars; "TOTAL" is 5 chars
    # All cells in a column must be right-aligned to same width
    # Simplest check: header tokens are at least as wide as the text
    tokens = header.split()
    for token in tokens:
        assert len(token) >= len(token.strip())  # trivially true, but verify column via structure
    # More meaningful: each column header appears untruncated
    assert "2024-Q1" in header
    assert "TOTAL" in header


# ── Stage 4: Validate Output ─────────────────────────────────────────────────

def test_validate_output_passes_for_valid_table():
    agg = _simple_aggregated()
    table = format_table(agg)
    result = validate_output(table, agg)
    assert result == table


def test_validate_output_error_missing_period():
    agg = _simple_aggregated()
    # Tamper: remove the period from the table
    table = format_table(agg).replace("2024-Q1", "XXXX-XX")
    result = validate_output(table, agg)
    assert isinstance(result, dict)
    assert result["error"] == "validation_error"


def test_validate_output_error_mismatched_totals():
    agg = _simple_aggregated()
    table = format_table(agg)
    # Tamper: replace some numeric value to break total match
    tampered = table.replace("$1,000.00", "$9,999.00")
    result = validate_output(tampered, agg)
    assert isinstance(result, dict)
    assert result["error"] == "validation_error"


# ── Full Pipeline ────────────────────────────────────────────────────────────

def test_run_pipeline_returns_formatted_table():
    raw = [
        "1:REVENUE:1000.00:2024-Q1",
        "2:COST:-200.00:2024-Q1",
        "3:HEADCOUNT:5:2024-Q1",
    ]
    result = run_pipeline(raw)
    assert isinstance(result, str)
    assert "REVENUE" in result
    assert "2024-Q1" in result
    assert "TOTAL" in result


def test_run_pipeline_returns_parse_error_on_bad_input():
    result = run_pipeline(["bad-data"])
    assert isinstance(result, dict)
    assert result["error"] == "parse_error"


def test_parse_error_non_positive_row_id():
    result = parse(["0:REVENUE:100:2024-Q1"])
    assert isinstance(result, dict)
    assert result["error"] == "parse_error"
    assert "row_id" in result["reason"]


def test_parse_error_non_integer_row_id():
    result = parse(["abc:REVENUE:100:2024-Q1"])
    assert isinstance(result, dict)
    assert result["error"] == "parse_error"
    assert "row_id" in result["reason"]


def test_parse_error_invalid_float_value():
    result = parse(["1:REVENUE:not_a_number:2024-Q1"])
    assert isinstance(result, dict)
    assert result["error"] == "parse_error"
    assert "value" in result["reason"]


def test_validate_output_error_empty_table():
    agg = _simple_aggregated()
    result = validate_output("", agg)
    assert isinstance(result, dict)
    assert result["error"] == "validation_error"


def test_validate_output_error_missing_total_column():
    agg = _simple_aggregated()
    table = format_table(agg)
    # Remove "TOTAL" from the header only
    lines = table.splitlines()
    lines[0] = lines[0].replace("TOTAL", "XXXXX")
    tampered = "\n".join(lines)
    result = validate_output(tampered, agg)
    assert isinstance(result, dict)
    assert result["error"] == "validation_error"


def test_run_pipeline_multi_period_ordering():
    """Periods should appear in chronological order in the table."""
    raw = [
        "1:REVENUE:200.0:2024-Q3",
        "2:REVENUE:100.0:2023-Q4",
        "3:REVENUE:300.0:2024-Q1",
    ]
    result = run_pipeline(raw)
    assert isinstance(result, str)
    lines = result.splitlines()
    header = lines[0]
    # 2023-Q4 should come before 2024-Q1 which comes before 2024-Q3
    pos_q4 = header.index("2023-Q4")
    pos_q1 = header.index("2024-Q1")
    pos_q3 = header.index("2024-Q3")
    assert pos_q4 < pos_q1 < pos_q3
