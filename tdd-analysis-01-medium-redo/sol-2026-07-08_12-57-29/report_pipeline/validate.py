"""Stage 4 – Validate the formatted table before export."""

from dataclasses import dataclass, field
from typing import Union

from .aggregate import AggregatedData
from .format import compute_layout, _fmt_value, _fmt_monetary

_SEP_LEN = 2  # two-space column separator


@dataclass
class ValidationError:
    reason: str
    stage: str = field(default="validate", init=False)


def _parse_number(s: str) -> float:
    """Parse a formatted cell value back to a float.

    Handles plain integers (headcount), ``$1,234.56`` and ``-$200.00``.
    """
    s = s.strip()
    if not s:
        return 0.0
    negative = s.startswith("-")
    if negative:
        s = s[1:]
    if s.startswith("$"):
        s = s[1:]
    s = s.replace(",", "")
    try:
        val = float(s)
    except ValueError:
        raise ValueError(f"Cannot parse '{s}' as a number")
    return -val if negative else val


def _extract_cells(line: str, label_width: int, col_keys: list, col_widths: dict) -> dict:
    """Extract the text content of each column in *line*.

    Returns a mapping ``col_key → stripped cell text``.
    """
    pos = label_width  # skip the label column
    result = {}
    for col in col_keys:
        pos += _SEP_LEN
        w = col_widths[col]
        result[col] = line[pos : pos + w].strip()
        pos += w
    return result


def validate_output(
    table: str, aggregated: AggregatedData
) -> Union[str, "ValidationError"]:
    """Validate the plain-text *table* against *aggregated* data.

    Checks:

    1. Every period from the input appears as a table column.
    2. The TOTAL column value for each category row equals the sum of
       that row's period values (within a small floating-point tolerance).
    3. No column is narrower than its header.

    Returns *table* unchanged on success, or a :class:`ValidationError`
    on the first failing check.
    """
    # ── Derive the expected layout (same logic as format_table) ──────
    label_width, col_keys, col_widths = compute_layout(aggregated)

    # ── Check 1: every input period appears as a column ──────────────
    for period in aggregated.periods:
        if period not in col_keys:
            return ValidationError(
                reason=f"Period '{period}' missing from table columns"
            )
        # Also verify it appears in the actual table string
        if period not in table:
            return ValidationError(
                reason=f"Period '{period}' not found in formatted table"
            )

    # ── Check 3: no column narrower than its header ───────────────────
    for col in col_keys:
        if col_widths[col] < len(col):
            return ValidationError(
                reason=(
                    f"Column '{col}' width ({col_widths[col]}) is narrower "
                    f"than its header ({len(col)})"
                )
            )
    # Also check label column (header is blank, so always OK, but be explicit)
    if label_width < 0:
        return ValidationError(reason="Label column has negative width")

    # ── Check 2: TOTAL column = sum of period values per row ─────────
    lines = table.split("\n")
    # lines[0] = header; lines[1..n-1] = category rows; lines[-1] = TOTAL row
    category_lines = lines[1 : 1 + len(aggregated.categories)]

    for cat, line in zip(aggregated.categories, category_lines):
        try:
            cells = _extract_cells(line, label_width, col_keys, col_widths)
        except Exception as exc:
            return ValidationError(
                reason=f"Could not extract cells from row '{cat}': {exc}"
            )

        try:
            period_nums = [_parse_number(cells[p]) for p in aggregated.periods]
            total_num = _parse_number(cells["TOTAL"])
        except ValueError as exc:
            return ValidationError(
                reason=f"Could not parse values in row '{cat}': {exc}"
            )

        expected_total = sum(period_nums)
        if abs(expected_total - total_num) > 0.005:
            return ValidationError(
                reason=(
                    f"TOTAL mismatch in row '{cat}': "
                    f"sum of periods={expected_total:.4f}, "
                    f"TOTAL column={total_num:.4f}"
                )
            )

    return table
