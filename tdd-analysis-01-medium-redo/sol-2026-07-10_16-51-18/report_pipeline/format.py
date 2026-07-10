CATEGORIES = ["REVENUE", "COST", "HEADCOUNT"]


def _format_value(category, value):
    if category == "HEADCOUNT":
        return str(int(round(value)))
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def format_table(agg):
    """Format aggregated data into a plain-text table."""
    pc = agg["by_period_category"]
    periods = list(pc.keys())
    category_totals = agg["category_totals"]
    period_subtotals = agg["period_subtotals"]

    # Build rows of displayable values
    # rows: category -> {period: formatted_value, ..., "TOTAL": formatted_value}
    rows = {}
    for cat in CATEGORIES:
        row = {}
        cat_sum = 0.0
        for period in periods:
            val = pc[period].get(cat, 0.0)
            cat_sum += val
            row[period] = _format_value(cat, val)
        row["TOTAL"] = _format_value(cat, cat_sum)
        rows[cat] = row

    # TOTAL row
    total_row = {}
    for period in periods:
        total_row[period] = _format_value("REVENUE", period_subtotals.get(period, 0.0))
    grand_total = sum(period_subtotals.values())
    total_row["TOTAL"] = _format_value("REVENUE", grand_total)

    # Compute column widths
    col_names = periods + ["TOTAL"]
    col_widths = {}
    for col in col_names:
        header_len = len(col)
        vals = [rows[cat][col] for cat in CATEGORIES] + [total_row[col]]
        col_widths[col] = max(header_len, max(len(v) for v in vals))

    row_label_width = max(len(cat) for cat in CATEGORIES + ["TOTAL"])

    PAD = 2

    def fmt_row(label, row_vals):
        parts = [label.ljust(row_label_width)]
        for col in col_names:
            w = col_widths[col]
            parts.append(row_vals[col].rjust(w))
        return (" " * PAD).join(parts)

    # Header
    header_parts = [" " * row_label_width]
    for col in col_names:
        header_parts.append(col.rjust(col_widths[col]))
    header = (" " * PAD).join(header_parts)

    lines = [header]
    for cat in CATEGORIES:
        lines.append(fmt_row(cat, rows[cat]))
    lines.append(fmt_row("TOTAL", total_row))

    return "\n".join(lines)
