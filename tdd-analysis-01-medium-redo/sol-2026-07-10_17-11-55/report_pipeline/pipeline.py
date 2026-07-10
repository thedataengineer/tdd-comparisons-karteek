"""Full pipeline: parse → aggregate → format → validate."""
from .parse import parse
from .aggregate import aggregate
from .format_table import format_table
from .validate_output import validate_output


def run_pipeline(raw_rows: list[str]):
    """
    Run the full report pipeline.

    Stages:
      1. Parse raw strings into structured rows.
      2. Aggregate rows by period and category.
      3. Format aggregated data into a plain-text table.
      4. Validate the formatted table.

    Returns:
        str: the formatted table on success
        dict: a structured error from the failing stage
    """
    # Stage 1: Parse
    parsed = parse(raw_rows)
    if isinstance(parsed, dict):
        return parsed  # parse error

    # Stage 2: Aggregate
    aggregated = aggregate(parsed)

    # Stage 3: Format
    table = format_table(aggregated)

    # Stage 4: Validate
    result = validate_output(table, aggregated)
    return result
