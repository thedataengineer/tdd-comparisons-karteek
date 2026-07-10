"""Stage 2 – Aggregate parsed rows by period × category."""

from dataclasses import dataclass
from typing import Dict, List

from .parse import ParsedRow

CATEGORY_ORDER: List[str] = ["REVENUE", "COST", "HEADCOUNT"]


@dataclass
class AggregatedData:
    """Holds the complete aggregation result.

    Attributes:
        period_category: Mapping ``period → category → total``.
        period_subtotals: Mapping ``period → sum-across-all-categories``.
        category_totals: Mapping ``category → grand-total-across-all-periods``.
        grand_total: Sum of all values across every period and category.
        periods: Periods in chronological order.
        categories: Categories present in the data, in REVENUE/COST/HEADCOUNT order.
    """

    period_category: Dict[str, Dict[str, float]]
    period_subtotals: Dict[str, float]
    category_totals: Dict[str, float]
    grand_total: float
    periods: List[str]
    categories: List[str]


def _period_sort_key(period: str):
    year, q = period.split("-")
    return (int(year), int(q[1]))


def aggregate(rows: List[ParsedRow]) -> AggregatedData:
    """Group and sum rows by period × category.

    Returns an :class:`AggregatedData` containing per-cell totals,
    per-period subtotals, and per-category grand totals.  Periods are
    ordered chronologically; categories follow REVENUE → COST →
    HEADCOUNT order.
    """
    period_category: Dict[str, Dict[str, float]] = {}

    for row in rows:
        if row.period not in period_category:
            period_category[row.period] = {}
        period_category[row.period][row.category] = (
            period_category[row.period].get(row.category, 0.0) + row.value
        )

    periods = sorted(period_category.keys(), key=_period_sort_key)

    # Collect which categories appear, in canonical order
    all_cats_seen: set = set()
    for cat_map in period_category.values():
        all_cats_seen.update(cat_map.keys())
    categories = [c for c in CATEGORY_ORDER if c in all_cats_seen]

    # Fill missing cells with 0.0
    for period in periods:
        for cat in categories:
            period_category[period].setdefault(cat, 0.0)

    # Period subtotals (sum over all categories for a given period)
    period_subtotals: Dict[str, float] = {
        period: sum(period_category[period][cat] for cat in categories)
        for period in periods
    }

    # Category grand totals (sum over all periods for a given category)
    category_totals: Dict[str, float] = {
        cat: sum(period_category[period][cat] for period in periods)
        for cat in categories
    }

    grand_total = sum(category_totals.values())

    return AggregatedData(
        period_category=period_category,
        period_subtotals=period_subtotals,
        category_totals=category_totals,
        grand_total=grand_total,
        periods=periods,
        categories=categories,
    )
