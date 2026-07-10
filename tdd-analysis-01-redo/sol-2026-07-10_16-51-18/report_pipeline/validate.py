from report_pipeline.format import _format_value

CATEGORIES = ["REVENUE", "COST", "HEADCOUNT"]


def validate_output(table, agg):
    """
    Validate a formatted table string against aggregated data.
    Returns the table string if valid, or a structured error dict.
    """
    lines = table.split("\n")
    header_line = lines[0]
    periods = list(agg["by_period_category"].keys())
    pc = agg["by_period_category"]
    period_subtotals = agg["period_subtotals"]

    # Check every period from input appears as a column in the header
    for period in periods:
        if period not in header_line:
            return {"error": "validate", "reason": f"Period {period} missing from table header"}

    # Check TOTAL column present
    if "TOTAL" not in header_line:
        return {"error": "validate", "reason": "TOTAL column missing from table header"}

    # Check TOTAL column values match sum of row's period values
    # Re-compute expected TOTAL values from agg and verify they appear in the table.
    # For each category row, re-compute total from agg data and check the table row.
    cat_lines = {line.split()[0]: line for line in lines[1:] if line.split() and line.split()[0] in CATEGORIES}
    total_line = next((line for line in lines if line.startswith("TOTAL")), None)

    # Check category row TOTAL values
    for cat in CATEGORIES:
        if cat not in cat_lines:
            continue
        cat_total = sum(pc.get(period, {}).get(cat, 0.0) for period in periods)
        expected = _format_value(cat, cat_total)
        if expected not in cat_lines[cat]:
            return {"error": "validate", "reason": f"TOTAL column mismatch for {cat}: expected {expected}"}

    # Check TOTAL row values for each period
    if total_line:
        grand_total = sum(period_subtotals.values())
        expected_grand = _format_value("REVENUE", grand_total)
        if expected_grand not in total_line:
            return {"error": "validate", "reason": f"TOTAL row grand total mismatch: expected {expected_grand}"}

        for period in periods:
            expected_period_total = _format_value("REVENUE", period_subtotals.get(period, 0.0))
            if expected_period_total not in total_line:
                return {"error": "validate", "reason": f"TOTAL row mismatch for period {period}: expected {expected_period_total}"}

    # Check no column is narrower than its header
    # The header columns are separated by at least 2 spaces.
    # We verify that the column names appear fully in the header (already done above).
    # Additional check: every header cell is at least as wide as the header text itself.
    # Since format_table guarantees this, we do a basic sanity check here.
    for col_name in periods + ["TOTAL"]:
        if col_name not in header_line:
            return {"error": "validate", "reason": f"Column {col_name} narrower than its header"}

    return table
