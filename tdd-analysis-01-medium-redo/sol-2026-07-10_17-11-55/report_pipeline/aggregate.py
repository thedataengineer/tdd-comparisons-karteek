"""Aggregate stage: group parsed rows by period and category."""
from decimal import Decimal
from collections import defaultdict

CATEGORY_ORDER = ["REVENUE", "COST", "HEADCOUNT"]


def _period_sort_key(period: str) -> tuple:
    """Return a sort key for period strings like '2024-Q3'."""
    year, quarter = period.split("-")
    return int(year), int(quarter[1])


def aggregate(parsed_rows: list[dict]) -> dict:
    """
    Group parsed rows by PERIOD and CATEGORY, summing VALUES.

    Returns a dict with:
        cells: dict mapping (period, category) -> Decimal total
        period_totals: dict mapping period -> Decimal sum of all categories
        category_totals: dict mapping category -> Decimal sum across all periods
        periods: list of periods in chronological order
        categories: list of categories present, in fixed order (REVENUE, COST, HEADCOUNT)
    """
    cells: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    periods_seen = set()
    categories_seen = set()

    for row in parsed_rows:
        period = row["period"]
        category = row["category"]
        value = row["value"]
        cells[(period, category)] += value
        periods_seen.add(period)
        categories_seen.add(category)

    periods = sorted(periods_seen, key=_period_sort_key)
    categories = [c for c in CATEGORY_ORDER if c in categories_seen]

    # Convert defaultdict to regular dict
    cells = dict(cells)

    period_totals = {
        p: sum((cells.get((p, c), Decimal("0")) for c in categories), Decimal("0"))
        for p in periods
    }

    category_totals = {
        c: sum((cells.get((p, c), Decimal("0")) for p in periods), Decimal("0"))
        for c in categories
    }

    return {
        "cells": cells,
        "periods": periods,
        "categories": categories,
        "period_totals": period_totals,
        "category_totals": category_totals,
    }
