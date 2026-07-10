"""report_pipeline – formatting pipeline for plain-text financial reports."""

from .parse import parse, ParsedRow, ParseError
from .aggregate import aggregate, AggregatedData
from .format import format_table
from .validate import validate_output, ValidationError
from .pipeline import run_pipeline

__all__ = [
    "parse",
    "ParsedRow",
    "ParseError",
    "aggregate",
    "AggregatedData",
    "format_table",
    "validate_output",
    "ValidationError",
    "run_pipeline",
]
