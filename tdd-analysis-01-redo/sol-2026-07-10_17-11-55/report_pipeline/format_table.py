"""Format stage: transform aggregated data into a plain-text table."""
from decimal import Decimal

MIN_PADDING = 2  # minimum spaces between columns


def _format_value(value: Decimal, category: str) -> str:
    """Format a value based on its category."""
    if category == "HEADCOUNT":
        return str(int(value))
    else:
        # REVENUE, COST, and TOTAL rows use $, thousands separator, 2 decimal places
        abs_val = abs(value)
        # Format with thousands separator and 2 decimal places
        formatted = f"${abs_val:,.2f}"
        if value < 0:
            return f"-{formatted}"
        return formatted


def format_table(aggregated: dict) -> str:
    """
    Transform aggregated data into a plain-text table.

    The table has:
    - Header row with period columns (chronological) + TOTAL column
    - One row per category
    - TOTAL row at the bottom
    - Right-aligned values, column width = max(header width, widest value)
    - At least 2 spaces of padding between columns
    """
    periods = aggregated["periods"]
    categories = aggregated["categories"]
    cells = aggregated["cells"]
    period_totals = aggregated["period_totals"]
    category_totals = aggregated["category_totals"]

    # Column labels: first col is the row label, then one per period, then TOTAL
    col_headers = periods + ["TOTAL"]

    # Build cell strings: rows × cols
    # row_labels[i] -> category name (or "TOTAL" for the last row)
    row_labels = categories + ["TOTAL"]

    # Precompute formatted cell values
    # data_rows: list of (label, [values for each period col, TOTAL col])
    data_rows = []
    for cat in categories:
        row_vals = []
        for p in periods:
            v = cells.get((p, cat), Decimal("0"))
            row_vals.append(_format_value(v, cat))
        # TOTAL column for this category: sum across periods
        total_val = category_totals.get(cat, Decimal("0"))
        row_vals.append(_format_value(total_val, cat))
        data_rows.append((cat, row_vals))

    # TOTAL row: period totals + grand total
    # Use dollar format if any REVENUE or COST present, else integer format for pure HEADCOUNT
    total_fmt_cat = "HEADCOUNT" if categories and all(c == "HEADCOUNT" for c in categories) else "REVENUE"
    grand_total = sum(period_totals.values(), Decimal("0"))
    total_row_vals = []
    for p in periods:
        total_row_vals.append(_format_value(period_totals.get(p, Decimal("0")), total_fmt_cat))
    total_row_vals.append(_format_value(grand_total, total_fmt_cat))
    data_rows.append(("TOTAL", total_row_vals))

    # Determine column widths
    # First column: row labels
    first_col_width = max(len(label) for label, _ in data_rows)
    # Don't forget the header - but first col header is empty in some formats
    # We'll use "" as the first col header and pad to first_col_width

    # For each data column (period + TOTAL), compute max width
    num_data_cols = len(col_headers)
    col_widths = []
    for i, header in enumerate(col_headers):
        max_w = len(header)
        for _, row_vals in data_rows:
            if i < len(row_vals):
                max_w = max(max_w, len(row_vals[i]))
        col_widths.append(max_w)

    # Build rows
    sep = " " * MIN_PADDING

    def build_line(label, vals):
        parts = [label.ljust(first_col_width)]
        for i, val in enumerate(vals):
            parts.append(val.rjust(col_widths[i]))
        return sep.join(parts)

    # Header line
    header_parts = [" " * first_col_width]
    for i, header in enumerate(col_headers):
        header_parts.append(header.rjust(col_widths[i]))
    header_line = sep.join(header_parts)

    lines = [header_line]
    for label, vals in data_rows:
        lines.append(build_line(label, vals))

    return "\n".join(lines)
