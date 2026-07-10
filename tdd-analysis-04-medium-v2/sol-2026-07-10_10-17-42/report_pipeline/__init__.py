"""Report formatting pipeline – public API."""

from .models import ParsedRow, ParseError, AggregatedData, FormatError, PipelineError
from .parse import parse
from .aggregate import aggregate
from .format_stage import format_table
from .validate_stage import validate_output
from .pipeline import run_pipeline

__all__ = [
    "ParsedRow",
    "ParseError",
    "AggregatedData",
    "FormatError",
    "PipelineError",
    "parse",
    "aggregate",
    "format_table",
    "validate_output",
    "run_pipeline",
]
