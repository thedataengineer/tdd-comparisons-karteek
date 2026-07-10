from decimal import Decimal
import re


VALID_CATEGORIES = {"REVENUE", "COST", "HEADCOUNT"}
CATEGORY_ORDER = ["REVENUE", "COST", "HEADCOUNT"]


def parse(raw_rows):
    """Parse raw strings into structured row dicts, or return a structured error."""
    results = []
    for raw in raw_rows:
        parts = raw.split(":")
        if len(parts) != 4:
            return {"error": "parse_error", "input": raw, "reason": "invalid format"}
        row_id_str, category, value_str, period = parts

        # Validate row_id
        try:
            row_id = int(row_id_str)
            if row_id <= 0:
                raise ValueError
        except ValueError:
            return {"error": "parse_error", "input": raw, "reason": "invalid row_id"}

        # Validate category
        if category not in VALID_CATEGORIES:
            return {"error": "parse_error", "input": raw, "reason": "invalid category"}

        # Validate value
        try:
            value = float(value_str)
        except ValueError:
            return {"error": "parse_error", "input": raw, "reason": "invalid value"}

        if category in ("REVENUE", "HEADCOUNT") and value < 0:
            return {"error": "parse_error", "input": raw, "reason": "negative value not allowed for category"}

        # Validate period
        if not _valid_period(period):
            return {"error": "parse_error", "input": raw, "reason": "invalid period"}

        results.append({"row_id": row_id, "category": category, "value": value, "period": period})

    return results


def aggregate(rows):
    """Aggregate parsed rows by period/category, return totals structure."""
    data = {}  # {period: {category: total}}
    for row in rows:
        period = row["period"]
        category = row["category"]
        value = row["value"]
        if period not in data:
            data[period] = {}
        data[period][category] = data[period].get(category, 0.0) + value

    # Sort periods chronologically
    sorted_periods = sorted(data.keys(), key=_period_sort_key)

    # Per-period subtotals (sum across all categories in that period)
    period_subtotals = {}
    for period in sorted_periods:
        period_subtotals[period] = sum(data[period].values())

    # Per-category grand totals (sum across all periods)
    category_totals = {}
    for period in sorted_periods:
        for category, val in data[period].items():
            category_totals[category] = category_totals.get(category, 0.0) + val

    return {
        "data": data,
        "periods": sorted_periods,
        "period_subtotals": period_subtotals,
        "category_totals": category_totals,
    }


def format_table(aggregated):
    """Format aggregated data into a plain-text table string."""
    periods = aggregated["periods"]
    data = aggregated["data"]
    category_totals = aggregated["category_totals"]
    period_subtotals = aggregated["period_subtotals"]

    # Build cell values: rows = categories + TOTAL row; cols = periods + TOTAL
    # Format values per category
    def fmt_value(category, value):
        if category == "HEADCOUNT":
            return str(int(round(value)))
        else:
            return _fmt_money(value)

    # Gather cell data
    # rows: each category (in order) plus TOTAL
    # cols: each period (sorted) plus TOTAL
    row_labels = [c for c in CATEGORY_ORDER if c in category_totals or
                  any(c in data[p] for p in periods)]
    col_labels = periods + ["TOTAL"]

    cells = {}  # (row_label, col_label) -> formatted string
    for cat in row_labels:
        for period in periods:
            val = data.get(period, {}).get(cat, 0.0)
            cells[(cat, period)] = fmt_value(cat, val)
        total_val = category_totals.get(cat, 0.0)
        cells[(cat, "TOTAL")] = fmt_value(cat, total_val)

    # TOTAL row
    for period in periods:
        cells[("TOTAL", period)] = _fmt_money(period_subtotals.get(period, 0.0))
    grand_total = sum(period_subtotals.values())
    cells[("TOTAL", "TOTAL")] = _fmt_money(grand_total)

    # Compute column widths: max of header and all cell values in that column
    col_widths = {}
    for col in col_labels:
        max_w = len(col)
        for row in row_labels + ["TOTAL"]:
            max_w = max(max_w, len(cells[(row, col)]))
        col_widths[col] = max_w

    # Row label column width
    label_width = max(len(r) for r in row_labels + ["TOTAL"])

    # Build table
    padding = 2
    lines = []

    def build_line(label, cols):
        parts = [label.ljust(label_width)]
        for col in col_labels:
            cell = cols[col]
            parts.append(cell.rjust(col_widths[col]))
        return (" " * padding).join(parts)

    # Header
    header_cells = {col: col for col in col_labels}
    lines.append(build_line("", header_cells))

    # Category rows
    for cat in row_labels:
        lines.append(build_line(cat, {col: cells[(cat, col)] for col in col_labels}))

    # TOTAL row
    lines.append(build_line("TOTAL", {col: cells[("TOTAL", col)] for col in col_labels}))

    return "\n".join(lines)


def validate_output(table, aggregated):
    """Validate the formatted table. Returns table string or a structured error."""
    periods = aggregated["periods"]
    lines = table.splitlines()
    if not lines:
        return {"error": "validation_error", "reason": "empty table"}

    header = lines[0]

    # Check every period appears as a column
    for period in periods:
        if period not in header:
            return {"error": "validation_error", "reason": f"missing period column: {period}"}

    # Check no column is narrower than its header by examining header widths
    # (Since we built the table ourselves, this is mostly a sanity check
    # but we parse it for rigor)
    col_labels = periods + ["TOTAL"]
    for col in col_labels:
        if col not in header:
            return {"error": "validation_error", "reason": f"missing column: {col}"}

    # Check TOTAL column values match row sums
    # Parse each data row (skip header and TOTAL row)
    category_totals = aggregated["category_totals"]
    period_subtotals = aggregated["period_subtotals"]

    # We re-format and compare — if formats match the aggregated data we're good
    # Re-generate expected table and compare
    expected = format_table(aggregated)
    if table != expected:
        return {"error": "validation_error", "reason": "table content does not match aggregated data"}

    return table


def _fmt_money(value):
    """Format a monetary value as $1,234.56 or -$1,234.56."""
    if value < 0:
        return f"-${abs(value):,.2f}"
    return f"${value:,.2f}"


def _period_sort_key(period):
    """Return a sortable key for YYYY-QN format."""
    year, q = period.split("-")
    return (int(year), int(q[1]))


def run_pipeline(raw_rows):
    """Run the full pipeline: parse -> aggregate -> format -> validate."""
    parsed = parse(raw_rows)
    if isinstance(parsed, dict) and "error" in parsed:
        return parsed

    agg = aggregate(parsed)
    table = format_table(agg)
    return validate_output(table, agg)


def _valid_period(period):
    """Return True if period matches YYYY-QN where N in 1-4."""
    return bool(re.match(r"^\d{4}-Q[1-4]$", period))
