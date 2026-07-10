## 2. TDD Process Analysis

### Overall TDD Adherence: **Moderate (partial compliance)**

#### ✅ What Was Done Correctly

- **Each new callable (stage) was preceded by a failing test**: The agent wrote a test for `parse`, confirmed `ImportError` (red), then wrote the implementation. The same pattern was repeated for `aggregate`, `format_table`, `validate_output`, and `run_pipeline`.
- **Tests were added one at a time** within each stage, broadly following the "one test at a time" rule.
- **No test was weakened to adapt to an implementation**: There is no evidence of the agent softening assertions to make a failing test pass.
- **Coverage-driven additions**: After achieving ~92%, the agent systematically added tests for uncovered branches.
- **Full test suite was run after each implementation change**, confirming green state.

#### ⚠️ TDD Violations Observed

1. **Implementation was written before most tests within each stage**:  
   The agent wrote a **comprehensive implementation of `parse`** (handling all error cases: negative values, invalid categories, invalid period format, wrong field count) after only ONE test existed (`test_parse_single_revenue_row`). The subsequent 5 parse-error tests were added for code that was **already implemented** — violating the core TDD rule "never write implementation before there is a failing test requiring it".

   The same pattern was repeated for `format_table`: the COMPLETE implementation (including dollar formatting, negative formatting, headcount, column widths, etc.) was written after a single "returns string" test. Six subsequent format tests were written for already-existing code.

2. **Stub created before any test**:  
   The agent created an empty `pipeline.py` file (containing only a comment) before writing any test. While this is a minor violation (the file had no real implementation), it still technically put code before tests.

3. **The "fail first" cycle was skipped for error-case tests**:  
   Tests like `test_parse_negative_revenue_is_error`, `test_parse_invalid_period_format`, `test_parse_invalid_category` were added to the test file, then the tests were run and **immediately passed** (because the implementation was already complete). The agent did not pause to notice this and did not comment that these tests weren't red-first.

   The TDD instruction says: *"Run the test and confirm it fails (red). If it doesn't fail, the test isn't testing anything new — revise it."* This rule was systematically skipped for within-stage error behavior tests.

4. **Tests added for coverage, not behavior**:  
   Near the end, several tests were explicitly motivated by uncovered lines (e.g., `test_validate_output_empty_lines_skipped`, `test_validate_output_non_parseable_cell_skips_row`, `test_validate_output_cells_with_non_numeric_values_skipped`). These tests probe defensive/guard branches rather than user-facing behavior. This is more coverage-chasing than TDD.

---