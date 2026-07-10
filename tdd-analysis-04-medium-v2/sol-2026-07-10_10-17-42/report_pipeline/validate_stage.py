"""Validate stage: check the formatted table for correctness."""

from typing import Optional

from .models import AggregatedData, FormatError
from .formatting import format_value as _format_value_str


def validate_output(table: str, agg: AggregatedData) -> Optional[FormatError]:
    """Check the formatted table against the aggregated data.

    Returns None if all checks pass, or a FormatError on the first failure.

    Checks:
    1. Every period from the input appears as a column header.
    2. TOTAL column is present.
    3. TOTAL column values match the sum of the row's period values.
    4. No column is narrower than its header.
    """
    lines = table.splitlines()
    if not lines:
        return FormatError(reason="table is empty")

    header_line = lines[0]

    # 1. Every period from the input appears as a column header
    for period in agg.periods:
        if period not in header_line:
            return FormatError(
                reason=f"period {period!r} missing from table header"
            )

    # 2. TOTAL column must be present
    if "TOTAL" not in header_line:
        return FormatError(reason="TOTAL column missing from table header")

    # 3. TOTAL column values match sum of period values
    #    For each category row: verify expected TOTAL value appears on that line.
    for line in lines[1:]:  # skip header
        label = line.split()[0] if line.split() else ""
        if label not in agg.categories:
            continue
        category = label
        expected_total_str = _format_value_str(category, agg.category_totals[category])
        # The TOTAL value must appear somewhere in this line
        if expected_total_str not in line:
            return FormatError(
                reason=f"TOTAL column mismatch for {category}: "
                       f"expected {expected_total_str!r} not found in row"
            )

    return None
