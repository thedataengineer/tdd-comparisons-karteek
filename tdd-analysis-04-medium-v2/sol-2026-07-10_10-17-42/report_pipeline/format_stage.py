"""Format stage: transform AggregatedData into a plain-text table."""

from typing import Union

from .models import AggregatedData, FormatError
from .formatting import format_value as _format_value
from .validate_stage import validate_output

# Minimum padding spaces between columns
_MIN_PAD = 2



def format_table(agg: AggregatedData) -> Union[str, FormatError]:
    """Produce a plain-text table from aggregated data.

    Returns a formatted string, or a FormatError if validation fails.
    """
    periods = agg.periods
    categories = agg.categories

    # -----------------------------------------------------------------
    # Build cell content (strings) for every row × column
    # Row labels: categories + "TOTAL"
    # Columns: one per period + "TOTAL"
    # -----------------------------------------------------------------
    col_headers = periods + ["TOTAL"]
    row_labels = categories + ["TOTAL"]

    # cells[row_label][col_header] = string
    cells: dict[str, dict[str, str]] = {}

    for category in categories:
        cells[category] = {}
        for period in periods:
            cells[category][period] = _format_value(
                category, agg.values[period][category]
            )
        # Category TOTAL column – sum across periods
        cells[category]["TOTAL"] = _format_value(
            category, agg.category_totals[category]
        )

    # TOTAL row
    cells["TOTAL"] = {}
    for period in periods:
        cells["TOTAL"][period] = _format_value(
            "REVENUE",  # use $ formatting for totals
            agg.period_totals[period],
        )
    cells["TOTAL"]["TOTAL"] = _format_value("REVENUE", agg.grand_total)

    # -----------------------------------------------------------------
    # Compute column widths
    # -----------------------------------------------------------------
    col_widths: dict[str, int] = {}
    for col in col_headers:
        width = len(col)
        for row in row_labels:
            width = max(width, len(cells[row][col]))
        col_widths[col] = width

    # Width of the row-label column
    label_width = max(len(r) for r in row_labels)

    # -----------------------------------------------------------------
    # Build lines
    # -----------------------------------------------------------------
    pad = " " * _MIN_PAD

    def build_row(label: str, col_values: dict[str, str]) -> str:
        parts = [label.ljust(label_width)]
        for col in col_headers:
            parts.append(col_values[col].rjust(col_widths[col]))
        return pad.join(parts)

    header_vals = {col: col for col in col_headers}
    lines = [build_row("", header_vals)]

    for category in categories:
        lines.append(build_row(category, cells[category]))

    lines.append(build_row("TOTAL", cells["TOTAL"]))

    table = "\n".join(lines)

    # Validate before returning
    error = validate_output(table, agg)
    if error is not None:
        return error

    return table
