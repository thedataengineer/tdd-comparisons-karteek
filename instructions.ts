
// TDD instructions

export const without_tdd = `
Write tests alongside your implementation and aim for at least 80% line 
and branch coverage.

Your working directory is already a clean, isolated project folder — do 
not cd away from it.

Monitor the code coverage — aim for at least 80% line and branch coverage.
Install pytest-cov if needed by running 'python -m pip install pytest-cov' (use
'python -m pip', NOT bare 'pip', to ensure it goes into the active Python
environment). Once tests are passing, do a final coverage check with
'python -m pytest tests/ --cov=<foldername> --cov-report=term-missing'.

You're done when the task is complete — all spec behaviours implemented, tests passing, 
coverage above 80%.`

export const with_tdd = `
  You must complete this task using strict test-first development. Follow
this loop for every piece of behavior you implement:

1. Write ONE test for a single piece of behavior that does not yet exist
in the implementation.
2. Run the test and confirm it fails (red). If it doesn't fail, the test
   isn't testing anything new — revise it.
3. Write the minimum implementation code needed to make that test pass.
4. Run the full test suite and confirm everything passes (green).
5. Refactor if needed, re-running the suite to confirm it stays green.
6. Repeat from step 1 for the next piece of behavior.

Rules:
- Never write implementation code before there is a failing test that
requires it.
- Never write more than one new test at a time.
- Do not edit or weaken an existing test to make it pass. If you believe a
test was wrong, say so explicitly and explain why before changing it.
- Do not move on to the next test until the current one is green.
- Your working directory is already a clean, isolated project folder.
Do not cd to /tmp or any other directory to verify isolation — it is
already guaranteed.

Work through the rules in the task spec incrementally, one behavior at a
time, rather than trying to design the whole system up front. It's fine to
revisit and refactor earlier code as later tests reveal better designs.

Monitor the code coverage — aim for at least 80% line and branch coverage.
Install pytest-cov if needed by running 'python -m pip install pytest-cov' (use
'python -m pip', NOT bare 'pip', to ensure it goes into the active Python
environment). Once tests are passing, do a final coverage check with
'python -m pytest tests/ --cov=<foldername> --cov-report=term-missing'.
Keep adding tests until coverage is above 80%.

You're done when the task is complete — all spec behaviours implemented, tests passing, 
coverage above 80%.
  `;

export const with_tdd_improved = `
You must complete this task using strict test-first development. Follow
this loop for every piece of behavior you implement:

1. Write ONE test for a single piece of behavior that does not yet exist
in the implementation.
2. Run the test and confirm it fails (red). If it doesn't fail, the test
   isn't testing anything new — revise it.
3. Write the minimum implementation code needed to make that test pass.
4. Run the full test suite and confirm everything passes (green).
5. Refactor — every time the suite is green, pause
   and actively review the design before writing the next test:
   - Is the design still the best fit for
     the whole task, or was it frozen by an early minimal test? Improve it
     now, while the passing suite protects you.
   - Remove dead code, unused constants, and duplication; improve names.
   Re-run the suite after refactoring to confirm it stays green.
6. Repeat from step 1 for the next piece of behavior.

Rules:
- Never write implementation code before there is a failing test that
requires it.
- Never write more than one new test at a time.
- Do not edit or weaken an existing test to make it pass. If you believe a
test was wrong, say so explicitly and explain why before changing it.
- Do not move on to the next test until the current one is green.
- Your working directory is already a clean, isolated project folder.
Do not cd to /tmp or any other directory to verify isolation — it is
already guaranteed.

Design the CONTRACT up front; discover the IMPLEMENTATION incrementally.
Before your first test, read the whole spec and decide the shape of the
public interface and of any "structured result" the task asks for — what
fields it exposes, and how it reports which rule failed and why — so your
tests drive toward a deliberately-designed API rather than whatever the
first minimal test happens to freeze in place. Then work through the rules one behavior at a time, and keep revisiting that
design in the refactor step (5) as later tests reveal better shapes.

Monitor the code coverage — aim for at least 80% line and branch coverage.
Install pytest-cov if needed by running 'python -m pip install pytest-cov' (use
'python -m pip', NOT bare 'pip', to ensure it goes into the active Python
environment). Once tests are passing, do a final coverage check with
'python -m pytest tests/ --cov=<foldername> --cov-report=term-missing'.
Coverage above 80% is a floor, not the goal: a suite can reach 100% and
still miss whole categories of invalid input. Keep adding tests until the
coverage floor is met AND you have exercised the adversarial/boundary cases
described above.

You're done when the task is complete — all spec behaviours implemented, tests passing, 
coverage above 80%.
`;

export const tdd_expectations = `
The TDD instructions were: ${with_tdd}

Your job is to check if they were actually followed. In EVAL_DIR, you will find a report of what happened during
the task in a JSON file in the results directory. It should have a "conversation" property that contains everything
that happened during the session. 

- Check the tool calls to see if you can see the patterns for creating tests first, and running them first before even implementing
- Has the agent changed a test to adapt to an implementation? If so, how often did that happen and why? Did it help the agent discover a valuable learning in the process, or did the test not make sense at all in its first version?
- Check the conversation overall against the TDD instructions and see to which extent they were followed.
`;

// Tasks

export const task_small_slot_code_validator = `
Build a Python module that validates appointment slot codes used 
by a medical scheduling system.

A valid slot code must satisfy ALL of the following:
- Format is: {DAY}-{TIME}-{ROOM}-{CHECKSUM}
- DAY is a 3-letter uppercase weekday abbreviation: MON, TUE, WED, 
  THU, FRI only (no weekends)
- TIME is a 4-digit 24-hour clock value (HHMM), must be on the hour 
  or half hour, and must fall within 08:00–17:30 inclusive
- ROOM is 2 uppercase letters followed by 1–2 digits; the letters 
  must be one of: ER, IC, GP, OT
- CHECKSUM is a 2-digit number equal to the sum of the numeric 
  positions of the DAY's letters in the alphabet (A=1, Z=26), 
  plus the room number digits, modulo 100
  (e.g. MON = 13+15+14 = 42, room OT7 = 7, checksum = (42+7)%100 = 49)

Your module should expose a validation function that returns a 
structured result indicating whether the code is valid and, if not, 
which specific rule failed and why.
`

export const task_medium_report_export = `
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
`;

export const task_large_loyalty_rules = `
You are building a loyalty points engine for a retail company. Implement it 
in Python as a library (no UI, no database — in-memory state is fine) that 
exposes whatever functions/classes you think are appropriate for the rules 
below. Another engineer will import and call your code, so design the 
interface with that in mind.

DOMAIN RULES

1. Earning points
   - Customers earn points on purchases at a rate determined by their tier:
     Bronze: 1 point per $1 spent
     Silver: 1.25 points per $1 spent
     Gold: 1.5 points per $1 spent
   - Points from a purchase are awarded immediately and are rounded down to
     the nearest whole point.

2. Tiers
   - A customer's tier is determined by their total spend in the trailing
     365 days (not lifetime spend), recalculated after every purchase or
     refund:
     Bronze: $0–$999.99
     Silver: $1,000–$4,999.99
     Gold: $5,000+
   - Tier changes take effect immediately and apply to the purchase that
     triggered the change (i.e. if a purchase pushes someone from Bronze to
     Silver, that same purchase earns points at the Silver rate).

3. Expiration
   - Points expire on a rolling 90-day window from the date they were
     earned, EXCEPT points earned during the customer's signup month
     (month and year of their signup date) never expire.
   - When checking a customer's balance or attempting to spend points,
     expired points must not be counted or spendable.

4. Refunds
   - A refund on a purchase claws back the points earned from that specific
     purchase, but only up to however many of those points the customer has
     not already spent.
   - If the customer has already spent some of the points from the
     refunded purchase, claw back whatever is left of that batch; do not
     pull points from other purchases to make up the difference, and do not
     create a negative balance.
   - Refunds are matched to purchases by purchase ID. A purchase can only
     be refunded once.

5. Spending points
   - When a customer spends points, points are consumed oldest-batch-first
     (the batch from the earliest-dated purchase is drawn down before
     later batches), skipping any batch that has already fully expired.
   - Spending more points than the customer's current non-expired balance
     should be rejected (no partial spend, no negative balance).

6. Queries the system must support
   - Record a purchase (customer id, dollar amount, date) -> returns points
     earned and the customer's resulting tier.
   - Record a refund (purchase id, date) -> returns points clawed back.
   - Spend points (customer id, point amount, date) -> returns success/
     failure and remaining balance.
   - Get a customer's current spendable point balance as of a given date.
   - Get a customer's current tier as of a given date.

You may assume all dates are passed in explicitly (no need to read system
time). You may assume a customer's signup date is provided when the
customer is created.

Build this however you think is best designed. When you believe the work is 
complete, stop and report that you are done.
`;

// EVALUATION

export const evaluate_test_quality = `
Analysis of the final set of tests and their quality, beyond the measured coverage

- Are the tests and assertions meaningful?
- Are the tests well readable and expressively named?
- Do the tests add like good clients of their subject under test, or do they know too much about the internals?
- Do the tests use appropriate and realistic test data that covers the cases well?
- If mocks are used, are they appropriately used, or do they undermine the effectiveness of the test?
- Anything else that's fishy about the tests? Overengineered, underengineered, error-prone, brittle, ...?
`

export const create_solution_overview = `Create a supplementary report markdown file with

1. A summary of what was created: Description of the solution that was generated, starting with a mermaid diagram that is a class diagram of the solution. 

2. ${evaluate_test_quality}`
