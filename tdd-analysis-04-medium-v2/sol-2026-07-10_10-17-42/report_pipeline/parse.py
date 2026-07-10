"""Parse stage: convert raw strings into ParsedRow list or ParseError."""

from decimal import Decimal, InvalidOperation
from typing import Union

from .models import ParsedRow, ParseError

VALID_CATEGORIES = {"REVENUE", "COST", "HEADCOUNT"}


def parse(raw_rows: list[str]) -> Union[list[ParsedRow], ParseError]:
    """Parse a list of raw input strings.

    Returns a list of ParsedRow on success, or a ParseError if any
    input string is malformed.
    """
    parsed: list[ParsedRow] = []
    for raw in raw_rows:
        parts = raw.split(":")
        if len(parts) != 4:
            return ParseError(input_string=raw, reason="expected 4 colon-separated fields")

        row_id_str, category, value_str, period = parts

        # Validate ROW_ID
        if not row_id_str.isdigit() or int(row_id_str) <= 0:
            return ParseError(input_string=raw, reason=f"invalid ROW_ID: {row_id_str!r}")
        row_id = int(row_id_str)

        # Validate CATEGORY
        if category not in VALID_CATEGORIES:
            return ParseError(input_string=raw, reason=f"invalid CATEGORY: {category!r}")

        # Validate VALUE
        try:
            value = Decimal(value_str)
        except InvalidOperation:
            return ParseError(input_string=raw, reason=f"invalid VALUE: {value_str!r}")

        if value < 0 and category != "COST":
            return ParseError(
                input_string=raw,
                reason=f"negative VALUE only allowed for COST, got {category}",
            )

        # Validate PERIOD
        if not _valid_period(period):
            return ParseError(input_string=raw, reason=f"invalid PERIOD: {period!r}")

        parsed.append(ParsedRow(row_id=row_id, category=category, value=value, period=period))

    return parsed


def _valid_period(period: str) -> bool:
    """Return True if the period matches YYYY-QN (N in 1-4)."""
    if len(period) != 7:
        return False
    year_part, q_part = period[:4], period[4:]
    if not year_part.isdigit():
        return False
    if q_part not in ("-Q1", "-Q2", "-Q3", "-Q4"):
        return False
    return True
