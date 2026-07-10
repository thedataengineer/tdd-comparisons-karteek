"""Full pipeline: raw strings -> formatted table or structured error."""

from typing import List, Union

from .parse import parse, ParseError
from .aggregate import aggregate
from .format import format_table
from .validate import validate_output, ValidationError


def run_pipeline(raw_lines: List[str]) -> Union[str, ParseError, ValidationError]:
    """Run all pipeline stages in order.

    Returns the formatted table string on success, or the structured error
    from whichever stage failed first.
    """
    # Stage 1: Parse
    parsed = parse(raw_lines)
    if isinstance(parsed, ParseError):
        return parsed

    # Stage 2: Aggregate
    aggregated = aggregate(parsed)

    # Stage 3: Format
    table = format_table(aggregated)

    # Stage 4: Validate
    result = validate_output(table, aggregated)
    return result
