Build a Python module that transforms raw report data through a 
formatting pipeline, producing a plain-text report ready for export.

The pipeline stages, in order, are:

1. Parse
   Raw input is a list of strings, each in this format:
   "{ROW_ID}:{CATEGORY}:{VALUE}:{PERIOD}"
   - ROW_ID is a positive integer (unique within the input)
   - CATEGORY is one of: REVENUE, COST, HEADCOUNT
   - VALUE is a decimal number (may be negative for COST rows only; 
     a negative REVENUE or HEADCOUNT value is a parse error)
   - PERIOD is in the format YYYY-QN where N is 1–4 
     (e.g. 2024-Q1, 2023-Q4)
   Return a list of structured row values, or a structured error 
   identifying which input string failed and why.

2. Aggregate
   Group the parsed rows by PERIOD and CATEGORY. Within each group, 
   sum the VALUES. Return a structure that represents each 
   PERIOD × CATEGORY combination and its total, plus a per-period 
   subtotal and a per-category grand total across all periods.
   Periods should be ordered chronologically, categories in the 
   order: REVENUE, COST, HEADCOUNT.

3. Format
   Transform the aggregated data into a plain-text table. The table 
   must have:
   - A header row with period columns in chronological order, 
     plus a TOTAL column
   - One row per category, values right-aligned within their column
   - A TOTAL row at the bottom summing each period column
   - Column widths sized to the widest value in each column 
     (including header), with at least 2 spaces of padding between 
     columns
   - HEADCOUNT values formatted as plain integers
   - REVENUE and COST values formatted with a $ prefix, thousands 
     separator, and 2 decimal places (e.g. $1,234.56)
   - Negative values formatted with a leading minus sign outside 
     the $ (e.g. -$200.00)
   Return the formatted table as a string.

4. Validate output
   Before returning the formatted string, check that:
   - Every period from the input appears as a column
   - The TOTAL column values match the sum of the row's period values
   - No column is narrower than its header
   If any check fails, return a structured error rather than a 
   malformed table.

Expose each stage as a separate callable. Also expose a function 
that runs the full pipeline from raw input strings to a formatted 
table, returning either the table string or the structured error 
from whichever stage failed.

When you believe the work is complete, stop and report that you 
are done.