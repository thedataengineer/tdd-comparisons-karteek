"""Stage 2: Aggregate parsed rows by PERIOD and CATEGORY."""

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List

from .parse import ParsedRow

CATEGORY_ORDER = ["REVENUE", "COST", "HEADCOUNT"]


@dataclass
class AggregatedData:
    """Result of the aggregation stage.

    Attributes:
        periods: Chronologically ordered list of period strings.
        categories: Category names in canonical order.
        cells: Dict mapping (period, category) -> summed value.
        period_subtotals: Dict mapping period -> sum of all categories for that period.
        category_totals: Dict mapping category -> sum across all periods.
        grand_total: Sum across all periods and all categories.
    """
    periods: List[str]
    categories: List[str]
    cells: Dict[tuple, Decimal]
    period_subtotals: Dict[str, Decimal]
    category_totals: Dict[str, Decimal]
    grand_total: Decimal


def _period_sort_key(period: str):
    """Return a tuple (year, quarter) for chronological sorting."""
    year_str, q_str = period.split("-Q")
    return (int(year_str), int(q_str))


def aggregate(rows: List[ParsedRow]) -> AggregatedData:
    """Aggregate parsed rows and compute subtotals/totals."""
    cells: Dict[tuple, Decimal] = defaultdict(Decimal)
    periods_seen: set = set()
    categories_seen: set = set()

    for row in rows:
        key = (row.period, row.category)
        cells[key] += row.value
        periods_seen.add(row.period)
        categories_seen.add(row.category)

    # Order periods chronologically
    periods = sorted(periods_seen, key=_period_sort_key)

    # Order categories canonically; include only those present in data
    categories = [c for c in CATEGORY_ORDER if c in categories_seen]

    # Compute period subtotals (sum across all categories for each period)
    period_subtotals: Dict[str, Decimal] = {}
    for period in periods:
        period_subtotals[period] = sum(
            cells.get((period, cat), Decimal(0)) for cat in categories
        )

    # Compute category totals (sum across all periods for each category)
    category_totals: Dict[str, Decimal] = {}
    for cat in categories:
        category_totals[cat] = sum(
            cells.get((period, cat), Decimal(0)) for period in periods
        )

    grand_total = sum(period_subtotals.values())

    return AggregatedData(
        periods=periods,
        categories=categories,
        cells=dict(cells),
        period_subtotals=period_subtotals,
        category_totals=category_totals,
        grand_total=grand_total,
    )
