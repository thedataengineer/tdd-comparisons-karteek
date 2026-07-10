"""Parse stage: transform raw strings into structured row dicts."""
import re
from decimal import Decimal, InvalidOperation

VALID_CATEGORIES = {"REVENUE", "COST", "HEADCOUNT"}
PERIOD_PATTERN = re.compile(r"^\d{4}-Q[1-4]$")


def _make_error(input_str: str, reason: str) -> dict:
    return {"stage": "parse", "input": input_str, "reason": reason}


def parse(raw_rows: list[str]):
    """
    Parse a list of raw strings into structured row dicts.

    Each string must be in the format: "{ROW_ID}:{CATEGORY}:{VALUE}:{PERIOD}"

    Returns:
        list of dicts with keys: row_id, category, value, period
        OR a structured error dict if any row is invalid.
    """
    results = []
    seen_ids = set()

    for raw in raw_rows:
        parts = raw.split(":")
        if len(parts) != 4:
            return _make_error(raw, f"Expected 4 fields separated by ':', got {len(parts)}")

        row_id_str, category, value_str, period = parts

        # Validate row_id
        try:
            row_id = int(row_id_str)
        except ValueError:
            return _make_error(raw, f"ROW_ID must be a positive integer, got '{row_id_str}'")

        if row_id <= 0:
            return _make_error(raw, f"ROW_ID must be a positive integer, got {row_id}")

        if row_id in seen_ids:
            return _make_error(raw, f"Duplicate ROW_ID: {row_id}")
        seen_ids.add(row_id)

        # Validate category
        if category not in VALID_CATEGORIES:
            return _make_error(raw, f"Invalid category '{category}'; must be one of {sorted(VALID_CATEGORIES)}")

        # Validate value
        try:
            value = Decimal(value_str)
        except InvalidOperation:
            return _make_error(raw, f"VALUE must be a decimal number, got '{value_str}'")

        if category in ("REVENUE", "HEADCOUNT") and value < 0:
            return _make_error(raw, f"Negative VALUE is not allowed for category '{category}'")

        # Validate period
        if not PERIOD_PATTERN.match(period):
            return _make_error(raw, f"PERIOD must be in format YYYY-QN (N=1-4), got '{period}'")

        results.append({
            "row_id": row_id,
            "category": category,
            "value": value,
            "period": period,
        })

    return results
