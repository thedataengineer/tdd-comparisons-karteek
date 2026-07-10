"""Full pipeline: raw strings → formatted plain-text table."""

from typing import List, Union

from .parse import parse, ParseError
from .aggregate import aggregate
from .format import format_table
from .validate import validate_output, ValidationError


def run_pipeline(
    raw_inputs: List[str],
) -> Union[str, ParseError, ValidationError]:
    """Run all four pipeline stages in order.

    Stages:

    1. :func:`~report_pipeline.parse.parse` – parse raw strings.
    2. :func:`~report_pipeline.aggregate.aggregate` – aggregate by period/category.
    3. :func:`~report_pipeline.format.format_table` – produce plain-text table.
    4. :func:`~report_pipeline.validate.validate_output` – sanity-check the table.

    Returns the formatted table string on success, or the structured
    error from whichever stage failed first.
    """
    # Stage 1
    parsed = parse(raw_inputs)
    if isinstance(parsed, ParseError):
        return parsed

    # Stage 2
    aggregated = aggregate(parsed)

    # Stage 3
    table = format_table(aggregated)

    # Stage 4
    result = validate_output(table, aggregated)
    return result
