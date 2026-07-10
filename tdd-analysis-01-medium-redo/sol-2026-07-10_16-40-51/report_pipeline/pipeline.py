import re

_PERIOD_RE = re.compile(r'^\d{4}-Q[1-4]$')


def parse(raw_rows):
    result = []
    for raw in raw_rows:
        parts = raw.split(":")
        row_id = int(parts[0])
        category = parts[1]
        value = float(parts[2])
        period = parts[3]
        if category not in ("REVENUE", "COST", "HEADCOUNT"):
            return {"error": "parse", "input": raw, "reason": "invalid category"}
        if not _PERIOD_RE.match(period):
            return {"error": "parse", "input": raw, "reason": "invalid period format"}
        if category in ("REVENUE", "HEADCOUNT") and value < 0:
            return {"error": "parse", "input": raw, "reason": f"{category} value cannot be negative"}
        result.append({"row_id": row_id, "category": category, "value": value, "period": period})
    return result


CATEGORIES = ["REVENUE", "COST", "HEADCOUNT"]


def aggregate(parsed_rows):
    cells = {}  # period -> category -> total
    for row in parsed_rows:
        period = row["period"]
        category = row["category"]
        cells.setdefault(period, {})
        cells[period][category] = cells[period].get(category, 0.0) + row["value"]
    # Sort periods chronologically
    periods = sorted(cells.keys())
    # Per-period subtotals
    period_totals = {p: sum(cells[p].values()) for p in periods}
    # Per-category grand totals
    category_totals = {}
    for cat in CATEGORIES:
        category_totals[cat] = sum(cells[p].get(cat, 0.0) for p in periods)
    return {
        "cells": cells,
        "periods": periods,
        "period_totals": period_totals,
        "category_totals": category_totals,
    }


def _fmt_value(category, value):
    """Format a single value per its category rules."""
    if category == "HEADCOUNT":
        return str(int(round(value)))
    # REVENUE or COST
    if value < 0:
        return f"-${abs(value):,.2f}"
    return f"${value:,.2f}"


def format_table(aggregated):
    periods = aggregated["periods"]
    cells = aggregated["cells"]
    period_totals = aggregated["period_totals"]
    category_totals = aggregated["category_totals"]

    col_headers = periods + ["TOTAL"]
    row_labels = CATEGORIES + ["TOTAL"]

    # Build cell strings
    # rows: label -> col_header -> string
    data = {}
    for cat in CATEGORIES:
        data[cat] = {}
        for p in periods:
            val = cells.get(p, {}).get(cat, 0.0)
            data[cat][p] = _fmt_value(cat, val)
        data[cat]["TOTAL"] = _fmt_value(cat, category_totals[cat])
    # TOTAL row (period subtotals)
    data["TOTAL"] = {}
    for p in periods:
        data["TOTAL"][p] = _fmt_value("REVENUE", period_totals[p])
    grand_total = sum(period_totals.values())
    data["TOTAL"]["TOTAL"] = _fmt_value("REVENUE", grand_total)

    # Compute column widths (max of header and all cell values), +2 padding
    label_width = max(len(lbl) for lbl in row_labels)
    col_widths = {}
    for col in col_headers:
        max_w = len(col)
        for lbl in row_labels:
            max_w = max(max_w, len(data[lbl][col]))
        col_widths[col] = max_w

    # Build lines
    pad = 2
    def fmt_row(label, row_data):
        parts = [label.ljust(label_width)]
        for col in col_headers:
            parts.append(row_data[col].rjust(col_widths[col] + pad))
        return "".join(parts)

    header_data = {col: col for col in col_headers}
    lines = [fmt_row("", header_data)]
    for cat in CATEGORIES:
        lines.append(fmt_row(cat, data[cat]))
    lines.append(fmt_row("TOTAL", data["TOTAL"]))

    return "\n".join(lines)


def validate_output(formatted, aggregated):
    periods = aggregated["periods"]
    lines = formatted.splitlines()
    header = lines[0]

    # Check 1: every period from input appears as a column
    for p in periods:
        if p not in header:
            return {"error": "validate", "reason": f"period {p} missing from table"}

    # Check 2: no column narrower than its header
    for token in header.split():
        col_start = header.index(token)
        for line in lines[1:]:
            if len(line) < col_start:
                return {"error": "validate", "reason": f"column {token} is narrower than its header"}

    # Check 3: TOTAL column values match sum of row's period values
    expected = format_table(aggregated)
    if formatted != expected:
        return {"error": "validate", "reason": "TOTAL column values do not match row sums"}

    return formatted


def run_pipeline(raw_rows):
    parsed = parse(raw_rows)
    if isinstance(parsed, dict) and parsed.get("error"):
        return parsed
    aggregated = aggregate(parsed)
    formatted = format_table(aggregated)
    return validate_output(formatted, aggregated)
