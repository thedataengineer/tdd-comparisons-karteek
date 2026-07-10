from collections import defaultdict

CATEGORIES = ["REVENUE", "COST", "HEADCOUNT"]


def _period_sort_key(period):
    year, q = period.split("-Q")
    return (int(year), int(q))


def aggregate(rows):
    """Aggregate parsed rows by period and category."""
    by_period_category = defaultdict(lambda: defaultdict(float))

    for row in rows:
        by_period_category[row["period"]][row["category"]] += row["value"]

    # Convert to regular dict, sorted chronologically
    sorted_periods = sorted(by_period_category.keys(), key=_period_sort_key)
    pc = {period: dict(by_period_category[period]) for period in sorted_periods}

    # Period subtotals
    period_subtotals = {period: sum(cats.values()) for period, cats in pc.items()}

    # Category grand totals
    category_totals = defaultdict(float)
    for cats in pc.values():
        for cat, val in cats.items():
            category_totals[cat] += val
    category_totals = dict(category_totals)

    return {
        "by_period_category": pc,
        "period_subtotals": period_subtotals,
        "category_totals": category_totals,
    }
