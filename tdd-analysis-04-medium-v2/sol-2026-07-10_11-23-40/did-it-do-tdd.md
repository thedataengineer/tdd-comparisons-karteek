## 2. TDD Adherence Analysis

### Overall Pattern

The agent broadly followed TDD:
- Created stub implementations (`raise NotImplementedError`) before writing tests.
- Confirmed red failures before implementing for the primary tests.
- Verified green (full suite) after each implementation.
- No existing tests were weakened or deleted.

**12 labeled test checkpoints** across 43 tests were made.

### Red-Green Cycles Observed

The following key tests were properly confirmed as **RED before implementing**:
- Test 1 — parse single row → `NotImplementedError` FAIL → implemented → GREEN ✓  
- Test 5 — aggregate basic grouping → `NotImplementedError` FAIL → implemented → GREEN ✓  
- Test 7 — format_table basic structure → `NotImplementedError` FAIL → implemented → GREEN ✓  
- Test 9 — validate_output valid table → `NotImplementedError` FAIL → implemented → GREEN ✓  
- Test 11 — run_pipeline end-to-end → `NotImplementedError` FAIL → implemented → GREEN ✓

### TDD Rule Violations

**Significant: Multiple tests written at once** — The rule "Never write more than one new test at a time" was repeatedly violated:

| Label | Tests Added in One Batch | Count |
|-------|--------------------------|-------|
| Test 3 — parse errors | `test_parse_error_wrong_field_count`, `test_parse_error_negative_revenue`, `test_parse_error_negative_headcount`, `test_parse_error_unknown_category`, `test_parse_error_invalid_period_quarter`, `test_parse_error_invalid_period_format`, `test_parse_error_invalid_row_id`, `test_parse_error_zero_row_id`, `test_parse_error_invalid_value`, `test_parse_error_identifies_failing_row` | 10 |
| Test 6 — aggregate extras | `test_aggregate_periods_chronological_order`, `test_aggregate_categories_in_spec_order`, `test_aggregate_sums_within_period_category`, `test_aggregate_period_totals`, `test_aggregate_category_totals_across_periods`, `test_aggregate_missing_category_for_period_defaults_zero`, `test_aggregate_single_row` | 7 |
| Test 8 — format extras | `test_format_multiple_periods_in_header`, `test_format_column_no_narrower_than_header`, `test_format_two_spaces_padding_between_columns`, `test_format_negative_cost_has_minus_before_dollar` | 4 |
| Test 10 — validate extras | `test_validate_mismatched_category_total_returns_error`, `test_validate_mismatched_grand_total_returns_error`, `test_validate_missing_period_returns_validation_error` | 3 |
| Test 12 — validate coverage | `test_validate_empty_table_string_returns_error`, `test_validate_missing_total_column_returns_error`, plus 2 others | 4 |

**Why this happened:** The agent wrote more complete implementations than strictly minimal (e.g., after Test 1 the full parse function was implemented). Subsequent parse tests then passed immediately, so the agent added all remaining parse tests in one batch. A similar pattern occurred for aggregate and format.

**Minimal implementation violations:** After Test 1, the agent implemented the entire `parse()` function (not just the minimum to make one test pass), meaning Tests 2–4 passed immediately without red-green cycles. This suggests the agent prioritized implementation completeness over strict TDD discipline.

### Test Modifications

The agent did **not** weaken any existing test. All edits to test files were additive (inserting new tests, not modifying assertions). This is good.

### Coverage Achievement

100% line coverage was achieved — exceeding the 80% requirement significantly.
