from report_pipeline.parse import parse
from report_pipeline.aggregate import aggregate
from report_pipeline.format import format_table
from report_pipeline.validate import validate_output


def run_pipeline(raw_lines):
    """Run the full report pipeline from raw strings to formatted table."""
    parsed = parse(raw_lines)
    if isinstance(parsed, dict) and parsed.get("error"):
        return parsed

    agg = aggregate(parsed)
    table = format_table(agg)
    return validate_output(table, agg)
