"""Stage 1: Parse raw input strings into structured rows."""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import List, Union

VALID_CATEGORIES = {"REVENUE", "COST", "HEADCOUNT"}
PERIOD_RE = re.compile(r"^\d{4}-Q[1-4]$")


@dataclass
class ParsedRow:
    row_id: int
    category: str
    value: Decimal
    period: str


@dataclass
class ParseError:
    raw: str
    reason: str


def parse(raw_lines: List[str]) -> Union[List[ParsedRow], ParseError]:
    """Parse raw input strings into structured rows.

    Returns a list of ParsedRow on success, or a ParseError describing
    the first line that failed validation.
    """
    results: List[ParsedRow] = []
    seen_ids: set = set()

    for line in raw_lines:
        parts = line.split(":")
        if len(parts) != 4:
            return ParseError(raw=line, reason="expected 4 colon-separated fields")

        raw_id, category, raw_value, period = parts

        # Validate ROW_ID
        try:
            row_id = int(raw_id)
        except ValueError:
            return ParseError(raw=line, reason=f"ROW_ID is not an integer: {raw_id!r}")

        if row_id <= 0:
            return ParseError(raw=line, reason=f"ROW_ID must be a positive integer: {row_id}")

        if row_id in seen_ids:
            return ParseError(raw=line, reason=f"duplicate ROW_ID: {row_id}")
        seen_ids.add(row_id)

        # Validate CATEGORY
        if category not in VALID_CATEGORIES:
            return ParseError(raw=line, reason=f"unknown CATEGORY: {category!r}")

        # Validate VALUE
        try:
            value = Decimal(raw_value)
        except InvalidOperation:
            return ParseError(raw=line, reason=f"VALUE is not a valid decimal: {raw_value!r}")

        if category in ("REVENUE", "HEADCOUNT") and value < 0:
            return ParseError(
                raw=line,
                reason=f"negative VALUE not allowed for {category}: {raw_value}",
            )

        # Validate PERIOD
        if not PERIOD_RE.match(period):
            return ParseError(
                raw=line,
                reason=f"PERIOD must be YYYY-QN (N=1-4): {period!r}",
            )

        results.append(ParsedRow(row_id=row_id, category=category, value=value, period=period))

    return results
