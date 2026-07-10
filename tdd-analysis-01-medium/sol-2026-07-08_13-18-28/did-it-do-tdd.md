## 2. TDD Process Analysis

### Did the agent follow the red-green-refactor cycle?

**Partially.** The agent had a recognisable TDD skeleton, but deviated from strict TDD rules in several important ways:

#### Step 1 — First test, then implementation stub
The agent wrote `pipeline.py` as a 62-byte stub before writing `test_pipeline.py`. The first test `test_parse_single_valid_row` was written, then run (RED — ImportError: cannot import `parse`), which is correct.

#### Step 2 — Over-implementation after first RED
After the first test failure, the agent wrote `pipeline.py` with **1,690 bytes** — the _complete, fully-validated_ `parse()` function including all six error-path validations. Only one test existed at that point (`test_parse_single_valid_row`). This violates:
> "Write the minimum implementation code needed to make that test pass."

As a consequence, all subsequent parse-related tests (`test_parse_multiple_valid_rows`, `test_parse_error_invalid_format`, `test_parse_error_invalid_category`, `test_parse_error_negative_revenue`, `test_parse_error_negative_headcount`, `test_parse_error_invalid_period`) were added **without ever seeing RED**. Each test passed immediately because the implementation was already complete.

#### Step 3 — Two tests added at once (rule violation)
The agent added `test_parse_error_negative_revenue` AND `test_parse_error_negative_headcount` in a single `edit` call, violating:
> "Never write more than one new test at a time."

#### Step 4 — New-function RED via ImportError
For `aggregate`, `format_table`, `validate_output`, and `run_pipeline`, the agent first updated the import statement in the test file, ran tests (ImportError → RED), then implemented the function. This is a reasonable TDD approach: the import error serves as the "failing test." The full function was again written in one shot, meaning stage-specific tests added after implementation were never individually red.

#### Step 5 — No test was weakened
Examining all `edit` calls on `test_pipeline.py`, no test had its assertions softened or removed to make a failing test pass. Tests were only added, reordered, or expanded.

#### Step 6 — No RED for coverage-boosting tests
After seeing 97% coverage, the agent added 5 more tests to hit uncovered lines. These tests passed immediately (implementation already covered those paths), violating the requirement to see RED before GREEN.

### Summary table

| TDD Rule | Followed? |
|---|---|
| Write ONE test at a time | ❌ Violated once (two tests added together) |
| Confirm test fails (RED) before implementing | ❌ Violated repeatedly (parse-stage tests never RED; coverage tests never RED) |
| Write minimum implementation | ❌ Violated (full function written after first test) |
| Full suite must stay green | ✅ Always ran full suite |
| No test weakened | ✅ No tests were weakened |
| Coverage ≥ 80% | ✅ Achieved 100% |
