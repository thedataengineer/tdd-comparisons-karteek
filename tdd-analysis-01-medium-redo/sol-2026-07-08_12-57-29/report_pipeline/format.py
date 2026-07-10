"""Stage 3 – Format aggregated data into a plain-text table."""

from typing import Dict, List, Tuple

from .aggregate import AggregatedData

_SEP = "  "  # two-space column separator


# ── Value formatters ──────────────────────────────────────────────────────────

def _fmt_monetary(value: float) -> str:
    """Format a monetary value, e.g. 1234.56 → '$1,234.56', -200 → '-$200.00'."""
    if value < 0:
        return f"-${abs(value):,.2f}"
    return f"${value:,.2f}"


def _fmt_headcount(value: float) -> str:
    """Format a headcount value as a plain integer string."""
    return str(int(round(value)))


def _fmt_value(category: str, value: float) -> str:
    """Dispatch to the correct formatter based on category."""
    if category == "HEADCOUNT":
        return _fmt_headcount(value)
    return _fmt_monetary(value)


# ── Layout helper (shared with validate) ─────────────────────────────────────

def compute_layout(aggregated: AggregatedData) -> Tuple[int, List[str], Dict[str, int]]:
    """Return ``(label_width, col_keys, col_widths)`` for the table.

    *label_width*  – width of the leftmost (row-label) column.
    *col_keys*     – ordered list of column identifiers (periods + "TOTAL").
    *col_widths*   – mapping from col_key → allocated column width.
    """
    periods = aggregated.periods
    categories = aggregated.categories
    col_keys: List[str] = periods + ["TOTAL"]

    # Build all cell values so we can measure them
    # cell_values[col_key][row_label] = formatted string
    cell_values: Dict[str, Dict[str, str]] = {col: {} for col in col_keys}

    for cat in categories:
        for period in periods:
            val = aggregated.period_category[period][cat]
            cell_values[period][cat] = _fmt_value(cat, val)
        cell_values["TOTAL"][cat] = _fmt_value(cat, aggregated.category_totals[cat])

    # TOTAL row uses monetary formatting
    for period in periods:
        cell_values[period]["TOTAL"] = _fmt_monetary(aggregated.period_subtotals[period])
    cell_values["TOTAL"]["TOTAL"] = _fmt_monetary(aggregated.grand_total)

    all_row_labels = list(categories) + ["TOTAL"]

    # Label column: widest label (header for label column is blank)
    label_width = max((len(lbl) for lbl in all_row_labels), default=0)

    # Data columns: max of header width and all cell widths
    col_widths: Dict[str, int] = {}
    for col in col_keys:
        max_w = len(col)  # header text
        for lbl in all_row_labels:
            max_w = max(max_w, len(cell_values[col].get(lbl, "")))
        col_widths[col] = max_w

    return label_width, col_keys, col_widths


# ── Public formatter ──────────────────────────────────────────────────────────

def format_table(aggregated: AggregatedData) -> str:
    """Format *aggregated* data into a plain-text report table.

    Returns the table as a multi-line string.  Each data cell is
    right-aligned within its column; the row-label column is
    left-aligned.  Columns are separated by at least two spaces.
    """
    periods = aggregated.periods
    categories = aggregated.categories

    label_width, col_keys, col_widths = compute_layout(aggregated)

    def render_row(label: str, get_val) -> str:
        parts = [label.ljust(label_width)]
        for col in col_keys:
            parts.append(get_val(col).rjust(col_widths[col]))
        return _SEP.join(parts)

    lines: List[str] = []

    # Header
    lines.append(render_row("", lambda col: col))

    # Category rows
    for cat in categories:
        def _cat_val(col, _cat=cat):
            if col == "TOTAL":
                return _fmt_value(_cat, aggregated.category_totals[_cat])
            return _fmt_value(_cat, aggregated.period_category[col][_cat])

        lines.append(render_row(cat, _cat_val))

    # TOTAL row
    def _total_val(col):
        if col == "TOTAL":
            return _fmt_monetary(aggregated.grand_total)
        return _fmt_monetary(aggregated.period_subtotals[col])

    lines.append(render_row("TOTAL", _total_val))

    return "\n".join(lines)
