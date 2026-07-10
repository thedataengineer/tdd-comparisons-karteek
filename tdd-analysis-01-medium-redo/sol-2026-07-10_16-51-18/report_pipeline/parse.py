import re

VALID_PERIOD = re.compile(r'^\d{4}-Q[1-4]$')


def parse(raw_lines):
    """Parse raw report strings into structured row dicts."""
    rows = []
    for line in raw_lines:
        parts = line.split(":")
        row_id = int(parts[0])
        category = parts[1]
        value = float(parts[2])
        period = parts[3]

        if category not in ("REVENUE", "COST", "HEADCOUNT"):
            return {"error": "parse", "input": line, "reason": f"Invalid category: {category}"}

        if not VALID_PERIOD.match(period):
            return {"error": "parse", "input": line, "reason": f"Invalid period format: {period}"}

        if category in ("REVENUE", "HEADCOUNT") and value < 0:
            return {"error": "parse", "input": line, "reason": f"Negative value not allowed for {category}"}

        rows.append({"row_id": row_id, "category": category, "value": value, "period": period})
    return rows
