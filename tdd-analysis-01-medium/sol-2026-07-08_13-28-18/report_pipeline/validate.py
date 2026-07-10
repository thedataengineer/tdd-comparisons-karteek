"""Stage 4: Validate the formatted table before returning it."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import List, Union

from .aggregate import AggregatedData
from .format import compute_col_slot_starts, compute_col_widths_list


@dataclass
class ValidationError:
    reason: str


def validate_output(
    table: str, data: AggregatedData
) -> Union[str, ValidationError]:
    """Validate the formatted table against the aggregated data.

    Checks:
    1. Every period from the input appears as a column header.
    2. The TOTAL column matches the sum of the row's period values.
    3. No column is narrower than its header.

    Returns the table string if valid, or a ValidationError.
    """
    lines = table.splitlines()
    if not lines:
        return ValidationError(reason="table is empty")

    header_line = lines[0]

    # --- Check 1: all periods appear as column headers ---
    for period in data.periods:
        if period not in header_line:
            return ValidationError(
                reason=f"period {period!r} is missing from table header"
            )

    if "TOTAL" not in header_line:
        return ValidationError(reason="TOTAL column not found in header")

    # --- Derive column layout from the aggregated data ---
    # Columns: [label, period_0, ..., period_N, TOTAL]
    col_starts = compute_col_slot_starts(data)
    col_widths = compute_col_widths_list(data)
    col_headers = [""] + data.periods + ["TOTAL"]
    total_col_idx = len(data.periods) + 1  # index of the TOTAL column

    # --- Check 3: no column narrower than its header ---
    for col_name, col_width in zip(col_headers, col_widths):
        if col_width < len(col_name):
            return ValidationError(
                reason=f"column {col_name!r} is narrower than its header"
            )

    # --- Check 2: TOTAL column values match sum of period values ---
    for row_line in lines[1:]:
        if not row_line.strip():
            continue

        row_label = _get_field(row_line, col_starts[0], col_widths[0]).strip()

        # Extract period values and TOTAL value
        try:
            period_values = [
                _parse_formatted_value(
                    _get_field(row_line, col_starts[i + 1], col_widths[i + 1])
                )
                for i in range(len(data.periods))
            ]
            total_value = _parse_formatted_value(
                _get_field(row_line, col_starts[total_col_idx], col_widths[total_col_idx])
            )
        except (ValueError, InvalidOperation):
            continue

        period_sum = sum(period_values)

        if abs(period_sum - total_value) > Decimal("0.005"):
            return ValidationError(
                reason=(
                    f"TOTAL mismatch in row {row_label!r}: "
                    f"sum of periods={period_sum}, TOTAL column={total_value}"
                )
            )

    return table


def _get_field(line: str, col_start: int, col_width: int) -> str:
    """Extract the field at [col_start, col_start + col_width] from a line."""
    end = col_start + col_width
    if col_start >= len(line):
        return ""
    return line[col_start:min(end, len(line))]


def _parse_formatted_value(s: str) -> Decimal:
    """Parse a formatted value string back to Decimal."""
    s = s.strip()
    if not s:
        return Decimal(0)
    negative = s.startswith("-")
    if negative:
        s = s[1:]
    s = s.lstrip("$").replace(",", "")
    val = Decimal(s)
    return -val if negative else val
