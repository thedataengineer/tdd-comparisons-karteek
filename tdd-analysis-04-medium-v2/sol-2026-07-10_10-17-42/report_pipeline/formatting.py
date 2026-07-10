"""Shared value formatting utilities."""

from decimal import Decimal


def format_value(category: str, value: Decimal) -> str:
    """Format a numeric value according to its category rules.

    HEADCOUNT → plain integer.
    REVENUE / COST → $X,XXX.XX with leading minus for negatives (-$X.XX).
    The TOTAL row uses REVENUE-style ($ formatting).
    """
    if category == "HEADCOUNT":
        return str(int(value))
    negative = value < 0
    abs_val = abs(value)
    formatted = f"${abs_val:,.2f}"
    return f"-{formatted}" if negative else formatted
