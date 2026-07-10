"""Stage 1 – Parse raw report strings into structured rows."""

import re
from dataclasses import dataclass, field
from typing import List, Union

VALID_CATEGORIES = frozenset({"REVENUE", "COST", "HEADCOUNT"})
_PERIOD_RE = re.compile(r'^\d{4}-Q[1-4]$')


@dataclass
class ParsedRow:
    row_id: int
    category: str
    value: float
    period: str


@dataclass
class ParseError:
    raw: str
    reason: str
    stage: str = field(default="parse", init=False)


def parse(raw_inputs: List[str]) -> Union[List[ParsedRow], ParseError]:
    """Parse a list of raw report strings.

    Each string must have the format ``ROW_ID:CATEGORY:VALUE:PERIOD``.

    Returns a list of :class:`ParsedRow` on success, or a
    :class:`ParseError` identifying the first failing string and why.
    """
    results: List[ParsedRow] = []
    seen_ids: set = set()

    for raw in raw_inputs:
        parts = raw.split(":")
        if len(parts) != 4:
            return ParseError(
                raw=raw,
                reason=f"Expected 4 colon-separated fields, got {len(parts)}",
            )

        row_id_str, category, value_str, period = parts

        # ── ROW_ID ────────────────────────────────────────────────────
        try:
            row_id = int(row_id_str)
        except ValueError:
            return ParseError(
                raw=raw,
                reason=f"ROW_ID must be a positive integer, got '{row_id_str}'",
            )
        if row_id <= 0:
            return ParseError(
                raw=raw,
                reason=f"ROW_ID must be a positive integer, got '{row_id_str}'",
            )
        if row_id in seen_ids:
            return ParseError(
                raw=raw,
                reason=f"Duplicate ROW_ID: {row_id}",
            )
        seen_ids.add(row_id)

        # ── CATEGORY ──────────────────────────────────────────────────
        if category not in VALID_CATEGORIES:
            return ParseError(
                raw=raw,
                reason=(
                    f"CATEGORY must be one of REVENUE, COST, HEADCOUNT, "
                    f"got '{category}'"
                ),
            )

        # ── VALUE ─────────────────────────────────────────────────────
        try:
            value = float(value_str)
        except ValueError:
            return ParseError(
                raw=raw,
                reason=f"VALUE must be a decimal number, got '{value_str}'",
            )
        if category in ("REVENUE", "HEADCOUNT") and value < 0:
            return ParseError(
                raw=raw,
                reason=(
                    f"Negative VALUE not allowed for {category}, got {value}"
                ),
            )

        # ── PERIOD ────────────────────────────────────────────────────
        if not _PERIOD_RE.match(period):
            return ParseError(
                raw=raw,
                reason=(
                    f"PERIOD must be in format YYYY-QN (N=1–4), got '{period}'"
                ),
            )

        results.append(
            ParsedRow(row_id=row_id, category=category, value=value, period=period)
        )

    return results
