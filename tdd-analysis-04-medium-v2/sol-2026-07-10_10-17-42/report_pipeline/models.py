"""Data classes used across all pipeline stages."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Union


@dataclass
class ParsedRow:
    """A successfully parsed input row."""
    row_id: int
    category: str   # REVENUE | COST | HEADCOUNT
    value: Decimal
    period: str     # YYYY-QN


@dataclass
class ParseError:
    """Returned when a single input string cannot be parsed."""
    input_string: str
    reason: str


@dataclass
class AggregatedData:
    """Result of the aggregation stage."""
    periods: list[str]                              # chronological order
    categories: list[str]                           # REVENUE, COST, HEADCOUNT order
    values: dict[str, dict[str, Decimal]]           # period -> category -> total
    period_totals: dict[str, Decimal]               # period -> sum across categories
    category_totals: dict[str, Decimal]             # category -> sum across periods
    grand_total: Decimal                            # sum of all values


@dataclass
class FormatError:
    """Returned when the format or validation stage fails."""
    reason: str


@dataclass
class PipelineError:
    """Wraps the error from whichever stage of the pipeline failed."""
    stage: str                                      # 'parse' | 'format' | 'validate'
    error: Union[ParseError, FormatError]
