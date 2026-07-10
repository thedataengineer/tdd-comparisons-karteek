"""Full pipeline: raw strings → formatted table or structured error."""

from typing import Union

from .models import ParseError, FormatError, PipelineError
from .parse import parse
from .aggregate import aggregate
from .format_stage import format_table


def run_pipeline(raw_rows: list[str]) -> Union[str, PipelineError]:
    """Run all four pipeline stages and return the formatted table or an error.

    Stages:
    1. Parse
    2. Aggregate
    3. Format (includes validate internally)

    Returns:
        str: the formatted plain-text table on success.
        PipelineError: with the stage name and underlying error on failure.
    """
    # Stage 1: Parse
    parsed = parse(raw_rows)
    if isinstance(parsed, ParseError):
        return PipelineError(stage="parse", error=parsed)

    # Stage 2: Aggregate
    agg = aggregate(parsed)

    # Stage 3 + 4: Format (validate is embedded)
    result = format_table(agg)
    if isinstance(result, FormatError):
        return PipelineError(stage="format", error=result)

    return result
