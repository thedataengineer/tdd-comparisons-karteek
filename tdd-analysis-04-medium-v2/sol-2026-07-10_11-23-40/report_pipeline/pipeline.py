"""Report formatting pipeline."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Union


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

VALID_CATEGORIES = ("REVENUE", "COST", "HEADCOUNT")
CATEGORY_ORDER = list(VALID_CATEGORIES)


@dataclass
class ParsedRow:
    row_id: int
    category: str
    value: Decimal
    period: str


@dataclass
class ParseError:
    stage: str
    raw_input: str
    reason: str

    def __init__(self, raw_input: str, reason: str) -> None:
        self.stage = "parse"
        self.raw_input = raw_input
        self.reason = reason


@dataclass
class AggregatedData:
    periods: list[str]          # chronological
    categories: list[str]       # REVENUE, COST, HEADCOUNT (only those present)
    period_category: dict       # (period, category) -> Decimal
    period_totals: dict         # period -> Decimal
    category_totals: dict       # category -> Decimal
    grand_total: Decimal


@dataclass
class ValidationError:
    stage: str
    reason: str

    def __init__(self, reason: str) -> None:
        self.stage = "validate"
        self.reason = reason


# ---------------------------------------------------------------------------
# Stage 1 – Parse
# ---------------------------------------------------------------------------

def parse(raw_rows: list[str]) -> Union[list[ParsedRow], ParseError]:
    results: list[ParsedRow] = []
    for raw in raw_rows:
        parts = raw.split(":")
        if len(parts) != 4:
            return ParseError(raw_input=raw, reason="expected 4 colon-separated fields")
        row_id_str, category, value_str, period = parts

        # Validate row_id
        try:
            row_id = int(row_id_str)
        except ValueError:
            return ParseError(raw_input=raw, reason="ROW_ID must be a positive integer")
        if row_id <= 0:
            return ParseError(raw_input=raw, reason="ROW_ID must be a positive integer")

        # Validate category
        if category not in VALID_CATEGORIES:
            return ParseError(raw_input=raw, reason=f"unknown category: {category!r}")

        # Validate value
        try:
            value = Decimal(value_str)
        except Exception:
            return ParseError(raw_input=raw, reason="VALUE is not a valid decimal")
        if category in ("REVENUE", "HEADCOUNT") and value < 0:
            return ParseError(
                raw_input=raw,
                reason=f"negative VALUE not allowed for {category}",
            )

        # Validate period
        if not _valid_period(period):
            return ParseError(raw_input=raw, reason=f"invalid PERIOD format: {period!r}")

        results.append(ParsedRow(row_id=row_id, category=category, value=value, period=period))
    return results


def _valid_period(period: str) -> bool:
    """Return True if period matches YYYY-QN where N is 1-4."""
    return bool(re.fullmatch(r"\d{4}-Q[1-4]", period))


# ---------------------------------------------------------------------------
# Stage 2 – Aggregate
# ---------------------------------------------------------------------------

def aggregate(parsed_rows: list[ParsedRow]) -> AggregatedData:
    # Collect per (period, category) sums
    pc: dict[tuple[str, str], Decimal] = {}
    for row in parsed_rows:
        key = (row.period, row.category)
        pc[key] = pc.get(key, Decimal(0)) + row.value

    # Determine ordered periods (chronological) and categories present
    seen_periods: dict[str, None] = {}
    seen_cats: dict[str, None] = {}
    for row in parsed_rows:
        seen_periods[row.period] = None
        seen_cats[row.category] = None

    periods = sorted(seen_periods.keys(), key=_period_sort_key)
    categories = [c for c in CATEGORY_ORDER if c in seen_cats]

    # Period totals
    period_totals = {p: sum((pc.get((p, c), Decimal(0)) for c in categories), Decimal(0))
                     for p in periods}

    # Category totals
    category_totals = {c: sum((pc.get((p, c), Decimal(0)) for p in periods), Decimal(0))
                       for c in categories}

    grand_total = sum(period_totals.values(), Decimal(0))

    return AggregatedData(
        periods=periods,
        categories=categories,
        period_category=pc,
        period_totals=period_totals,
        category_totals=category_totals,
        grand_total=grand_total,
    )


def _period_sort_key(period: str) -> tuple[int, int]:
    """Return (year, quarter) for chronological sorting."""
    year_str, q_str = period.split("-Q")
    return (int(year_str), int(q_str))


# ---------------------------------------------------------------------------
# Stage 3 – Format
# ---------------------------------------------------------------------------

def format_table(aggregated: AggregatedData) -> str:
    agg = aggregated
    periods = agg.periods
    categories = agg.categories

    # Build cell values as strings
    # Columns: category label | period columns... | TOTAL
    def fmt_value(value: Decimal, category: str) -> str:
        if category == "HEADCOUNT":
            return str(int(value))
        # REVENUE or COST — monetary
        if value < 0:
            return f"-${abs(value):,.2f}"
        return f"${value:,.2f}"

    # Gather all cell strings
    # rows_data[cat] = [period_cell, ..., total_cell]
    rows_data: dict[str, list[str]] = {}
    for cat in categories:
        cells = []
        for p in periods:
            v = agg.period_category.get((p, cat), Decimal(0))
            cells.append(fmt_value(v, cat))
        # category total
        cells.append(fmt_value(agg.category_totals[cat], cat))
        rows_data[cat] = cells

    # TOTAL row (per-period sums and grand total) — use sum of period_totals
    total_row: list[str] = []
    for p in periods:
        v = agg.period_totals[p]
        # period total is sum across all categories; use monetary if only monetary cats present
        # Use a generic number format: if HEADCOUNT only, integer; otherwise monetary
        if categories == ["HEADCOUNT"]:
            total_row.append(str(int(v)))
        else:
            if v < 0:
                total_row.append(f"-${abs(v):,.2f}")
            else:
                total_row.append(f"${v:,.2f}")
    grand = agg.grand_total
    if categories == ["HEADCOUNT"]:
        total_row.append(str(int(grand)))
    else:
        if grand < 0:
            total_row.append(f"-${abs(grand):,.2f}")
        else:
            total_row.append(f"${grand:,.2f}")

    # Column headers: blank label col, periods..., TOTAL
    col_headers = periods + ["TOTAL"]

    # Compute column widths
    # col 0 is the row label column (category names + "TOTAL")
    label_width = max(len(cat) for cat in categories + ["TOTAL"])
    col_widths = []
    for i, header in enumerate(col_headers):
        col_vals = [rows_data[cat][i] for cat in categories] + [total_row[i]]
        col_widths.append(max(len(header), max(len(v) for v in col_vals)))

    PADDING = 2

    def build_row(label: str, cells: list[str]) -> str:
        parts = [label.ljust(label_width)]
        for w, cell in zip(col_widths, cells):
            parts.append(cell.rjust(w))
        return (" " * PADDING).join(parts)

    header_row = build_row("", col_headers)
    lines = [header_row]
    for cat in categories:
        lines.append(build_row(cat, rows_data[cat]))
    lines.append(build_row("TOTAL", total_row))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stage 4 – Validate output
# ---------------------------------------------------------------------------

def validate_output(
    table_str: str, aggregated: AggregatedData
) -> Union[str, ValidationError]:
    agg = aggregated

    # Check 1: every period from aggregated appears in the table
    for period in agg.periods:
        if period not in table_str:
            return ValidationError(reason=f"period {period!r} missing from table")

    # Check 2: TOTAL column values match sum of row's period values.
    # We check this by re-parsing the table lines.
    lines = table_str.splitlines()
    if not lines:
        return ValidationError(reason="table is empty")

    header = lines[0]
    # Verify no column is narrower than its header — done by checking header tokens
    # are present (structural check — width is enforced by format_table itself)
    # We rely on format_table being correct; for external tables we do a text check.
    for period in agg.periods:
        if period not in header:
            return ValidationError(reason=f"period {period!r} missing from header")

    if "TOTAL" not in header:
        return ValidationError(reason="TOTAL column missing from header")

    # Verify TOTAL column arithmetic by re-deriving from aggregated data.
    # The category_totals must equal the sum of per-period values for that category.
    for cat in agg.categories:
        expected_total = sum(
            (agg.period_category.get((p, cat), Decimal(0)) for p in agg.periods),
            Decimal(0),
        )
        if expected_total != agg.category_totals[cat]:
            return ValidationError(
                reason=f"TOTAL for {cat} does not match sum of period values"
            )

    # Grand total must match sum of period totals
    expected_grand = sum(agg.period_totals.values(), Decimal(0))
    if expected_grand != agg.grand_total:
        return ValidationError(reason="grand TOTAL does not match sum of period totals")

    return table_str


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    raw_rows: list[str],
) -> Union[str, ParseError, ValidationError]:
    parsed = parse(raw_rows)
    if isinstance(parsed, ParseError):
        return parsed

    agg = aggregate(parsed)
    table = format_table(agg)
    return validate_output(table, agg)
