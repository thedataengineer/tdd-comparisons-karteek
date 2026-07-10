"""Aggregate stage: group parsed rows by period × category and compute totals."""

from collections import defaultdict
from decimal import Decimal

from .models import AggregatedData, ParsedRow

CATEGORY_ORDER = ["REVENUE", "COST", "HEADCOUNT"]


def _period_sort_key(period: str) -> tuple[int, int]:
    """Return (year, quarter) tuple for chronological sorting."""
    year = int(period[:4])
    quarter = int(period[-1])
    return (year, quarter)


def aggregate(parsed_rows: list[ParsedRow]) -> AggregatedData:
    """Aggregate parsed rows into period × category totals."""
    # Accumulate values
    raw: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    periods_seen: set[str] = set()
    categories_seen: set[str] = set()

    for row in parsed_rows:
        raw[row.period][row.category] += row.value
        periods_seen.add(row.period)
        categories_seen.add(row.category)

    # Order periods chronologically
    periods = sorted(periods_seen, key=_period_sort_key)

    # Order categories per spec
    categories = [c for c in CATEGORY_ORDER if c in categories_seen]

    # Build values dict (fill missing combinations with zero)
    values: dict[str, dict[str, Decimal]] = {}
    for period in periods:
        values[period] = {}
        for category in categories:
            values[period][category] = raw[period].get(category, Decimal("0"))

    # Period totals (sum across categories for each period)
    period_totals: dict[str, Decimal] = {
        period: sum(values[period].values(), Decimal("0"))
        for period in periods
    }

    # Category totals (sum across periods for each category)
    category_totals: dict[str, Decimal] = {
        category: sum(values[period][category] for period in periods)
        for category in categories
    }

    grand_total = sum(period_totals.values(), Decimal("0"))

    return AggregatedData(
        periods=periods,
        categories=categories,
        values=values,
        period_totals=period_totals,
        category_totals=category_totals,
        grand_total=grand_total,
    )
