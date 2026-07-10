"""Stage 3: Format aggregated data as a plain-text table."""

from decimal import Decimal
from typing import Dict, List, Tuple

from .aggregate import AggregatedData

PADDING = 2  # minimum spaces between columns


def _format_value(category: str, value: Decimal) -> str:
    """Format a value according to its category rules."""
    if category == "HEADCOUNT":
        return str(int(value))
    else:
        # REVENUE or COST: $1,234.56 or -$200.00
        return _fmt_dollar(value)


def _fmt_dollar(value: Decimal) -> str:
    """Format as dollar amount: $1,234.56 or -$200.00."""
    abs_val = abs(value)
    formatted = f"${abs_val:,.2f}"
    if value < 0:
        return f"-{formatted}"
    return formatted


def _compute_col_widths(data: AggregatedData) -> Tuple[int, List[int], int]:
    """Compute column slot widths.

    Returns (label_width, period_widths, total_col_width).
    - label_width: width of the label column (col 0)
    - period_widths: list of widths for each period column (in order)
    - total_col_width: width of the TOTAL column
    """
    categories = data.categories
    periods = data.periods
    all_headcount = categories == ["HEADCOUNT"]

    # Label column
    label_candidates = [len(cat) for cat in categories] + [len("TOTAL")]
    label_width = max(label_candidates) if label_candidates else 0

    # Period columns
    period_widths: List[int] = []
    for period in periods:
        candidates = [len(period)]
        for cat in categories:
            val = data.cells.get((period, cat), Decimal(0))
            candidates.append(len(_format_value(cat, val)))
        # TOTAL row cell for this period
        ptotal = data.period_subtotals[period]
        candidates.append(len(_fmt_integer(ptotal) if all_headcount else _fmt_dollar(ptotal)))
        period_widths.append(max(candidates))

    # TOTAL column
    total_candidates = [len("TOTAL")]
    for cat in categories:
        val = data.category_totals.get(cat, Decimal(0))
        total_candidates.append(len(_format_value(cat, val)))
    grand = data.grand_total
    total_candidates.append(len(_fmt_integer(grand) if all_headcount else _fmt_dollar(grand)))
    total_col_width = max(total_candidates)

    return label_width, period_widths, total_col_width


def _fmt_integer(value: Decimal) -> str:
    return str(int(value))


def compute_col_slot_starts(data: AggregatedData) -> List[int]:
    """Return the start position of each column slot in the rendered table.

    Columns are: [label, period_0, period_1, ..., TOTAL]
    """
    label_width, period_widths, total_col_width = _compute_col_widths(data)
    starts = [0]
    pos = label_width + PADDING
    for pw in period_widths:
        starts.append(pos)
        pos += pw + PADDING
    starts.append(pos)
    return starts


def compute_col_widths_list(data: AggregatedData) -> List[int]:
    """Return column slot widths for all columns (label + periods + TOTAL)."""
    label_width, period_widths, total_col_width = _compute_col_widths(data)
    return [label_width] + period_widths + [total_col_width]


def format_table(data: AggregatedData) -> str:
    """Format aggregated data into a plain-text table string."""
    categories = data.categories
    periods = data.periods
    all_headcount = categories == ["HEADCOUNT"]

    label_width, period_widths, total_col_width = _compute_col_widths(data)
    col_widths = [label_width] + period_widths + [total_col_width]
    col_headers = [""] + periods + ["TOTAL"]

    # Build data rows
    rows_data: List[List[str]] = []
    for cat in categories:
        row = [cat]
        for period in periods:
            val = data.cells.get((period, cat), Decimal(0))
            row.append(_format_value(cat, val))
        total_val = data.category_totals.get(cat, Decimal(0))
        row.append(_format_value(cat, total_val))
        rows_data.append(row)

    # TOTAL row
    total_row = ["TOTAL"]
    for period in periods:
        val = data.period_subtotals[period]
        total_row.append(_fmt_integer(val) if all_headcount else _fmt_dollar(val))
    grand = data.grand_total
    total_row.append(_fmt_integer(grand) if all_headcount else _fmt_dollar(grand))

    all_rows = rows_data + [total_row]

    sep = " " * PADDING

    def render_row(cells: List[str]) -> str:
        parts = []
        for ci, cell in enumerate(cells):
            if ci == 0:
                parts.append(cell.ljust(col_widths[ci]))
            else:
                parts.append(cell.rjust(col_widths[ci]))
        return sep.join(parts)

    lines = [render_row(col_headers)]
    for row in all_rows:
        lines.append(render_row(row))

    return "\n".join(lines)
