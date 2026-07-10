# Comparison Report: Four Solutions to the Report-Pipeline Task

Task: build a Python module transforming raw `ROW_ID:CATEGORY:VALUE:PERIOD`
strings through a 4-stage pipeline (parse → aggregate → format → validate),
exposing each stage as a callable plus a full-pipeline entry point, returning
either a formatted table string or a structured error.

Four solutions were each analyzed independently (design, code quality, test
effectiveness), with every test suite actually executed and the pre-existing
self-analysis in each folder fact-checked against the code.

| # | Solution | Structure | Data types | Money | Tests | Result | Coverage |
|---|----------|-----------|-----------|-------|-------|--------|----------|
| 🥇 | `sol-…13-28-18` | module-per-stage | dataclasses | `Decimal` | 75 | 75 pass | 100% |
| 🥈 | `sol-…12-57-29` | module-per-stage | dataclasses | float/round | 107 | 107 pass | 100% |
| 🥉 | `sol-…13-18-28` | single module (TDD) | dicts | float | 30 | 30 pass | 100% |
| 4 | `sol-…13-41-45` | single module | dicts | float | 34 | 34 pass | 99% |

All four compile, run, and pass their own suites. They differ sharply on
**correctness of the validation stage** and **whether the tests would catch a
real regression**.

---

## Ranking rationale

### 🥇 1st — `sol-2026-07-08_13-28-18` (best overall)

**The only solution with no correctness bug on any legitimate input.**

- **Design (strongest):** clean module-per-stage layout, `@dataclass` row/error
  types, and `Decimal` throughout for money (the correct currency choice — the
  only solution to actually use it). Error-as-value union returns match the
  spec's "return a structured error" requirement. API shape matches the spec
  exactly.
- **Code quality:** readable, docstringed, well-named. Only minor issues:
  `int()` truncation of any fractional HEADCOUNT (parse never forbids one),
  a cosmetic `-$0.00` edge, and small duplication in the width/format ternary.
- **Tests (75):** genuinely strong parse error-path coverage (field count,
  non-int/zero/negative/**duplicate** ROW_ID, unknown category, negative
  REVENUE/HEADCOUNT, bad periods, first-error-only, `raw` preserved) — and it
  is the **only** solution that checks duplicate ROW_IDs.
- **Weaknesses:** the output validator is structurally coupled to the formatter
  (re-derives column layout from the same `AggregatedData` rather than parsing
  the rendered table), so a layout bug could partly self-certify. Format tests
  use substring checks, not snapshots, so padding/alignment regressions could
  slip through. One dead test (`test_format_column_widths_at_least_header_width`
  has **no assert**), plus a couple of `isinstance`-only "didn't crash" tests.

It wins because its happy path is correct end-to-end, its design and type
choices are the most idiomatic, and its error handling is the most thorough.

### 🥈 2nd — `sol-2026-07-08_12-57-29` (best-engineered, but a real bug)

Nearly co-first on design and by far the largest suite (107 tests, 100%
coverage), but it ships a genuine correctness defect.

- **Design:** same module-per-stage + dataclass structure as the winner, with
  the richest aggregate data structure and a shared `compute_layout` helper
  reused by format and validate (good DRY).
- **The bug (why it drops to 2nd):** `validate.py:118-119` re-parses the
  **rounded display text** and compares it to a **separately-rounded** TOTAL.
  Because each cell rounds independently, legitimate inputs with fractional
  headcount or sub-cent monetary values are **wrongly rejected by the
  pipeline** — the pipeline rejects its own valid output. This is the worst
  class of bug (false rejection of valid input), even though it only triggers
  on fractional values.
- **Second gap:** the TOTAL row (per-period subtotals + grand total) is
  **never validated** (`validate.py:100` iterates category rows only), and the
  width/period checks are effectively dead on real output because validate
  recomputes the same layout format used.
- **Tests:** broad and mostly meaningful, but the 100% coverage is partly
  inflated by monkeypatch-only defensive-branch tests, and no test uses
  fractional/sub-cent values, so the suite never exercises where the bug lives.
  `test_values_right_aligned_in_columns` is near-tautological.

Superb engineering and test breadth, held back by a real functional defect the
tests were structured never to find.

### 🥉 3rd — `sol-2026-07-08_13-18-28` (clean core, hollow validation)

Solid parse/aggregate/format, but stage 4 is theater.

- **Design:** single-module, dict-based rows/errors, float money (with an
  **unused `Decimal` import** — dead code). Workable but less self-documenting
  and type-safe than the dataclass solutions.
- **Correct where it counts:** money formatting, negative-sign placement,
  right-alignment, chronological + category ordering are all genuinely correct.
- **Validation is fake:** `validate_output` re-runs `format_table` on the same
  input and compares strings (`pipeline.py:175-184`). It never checks TOTAL
  columns against row sums, and the "column narrower than header" check is
  vacuous. The spec's stage-4 requirement is effectively unmet — and the tests
  reinforce the circularity rather than exposing it.
- Also accepts `nan`/`inf` values and ignores duplicate ROW_IDs.
- **Tests (30):** genuinely behavioral for the working stages, no tautologies
  in parse/aggregate/format — but they can't catch the validation defect
  because code and test share the same circular approach.

Placed above #4 because its core stages are correct, its validation weakness is
*harmless* (it doesn't reject valid input), and its tests don't enshrine a bug.

### 4th — `sol-2026-07-08_13-41-45` (a bug enshrined by its own tests)

Most compact, but the weakest correctness/testing combination.

- **Design:** single-module, dict-based, float money, unused `Decimal` import,
  plus a redundant inline `import re as _re` and convoluted `cats_present`
  logic.
- **Active logic bug:** the TOTAL row folds HEADCOUNT counts into dollar sums
  via `period_subtotals`, printing meaningless `$`-prefixed totals like
  `$805.00` (1000 − 200 + 5 people). Worse, **`test_aggregate_period_subtotals`
  asserts the buggy value (`810.0`) as correct** — the suite enshrines the bug.
- **Missing spec requirement:** validation Check #3 ("no column narrower than
  its header") is **not implemented in code** — the comment admits it only
  checks that header contains the period names. The test that claims to cover
  it asserts nothing (`isinstance(result, str)`).
- Also accepts `nan`/`inf` and duplicate ROW_IDs.
- **Tests (34):** decent parse/format error coverage, no mocks, but several
  hollow coverage-padding tests near the end, and the two issues above mean the
  green suite is actively misleading.

Ranks last because it combines an active output bug, a missing spec check, and
a test suite that certifies the bug as correct.

---

## Cross-cutting observations

- **HEADCOUNT summed into money totals** appears in **all four** solutions
  (period subtotals / grand total add person-counts to dollar figures and
  render them with `$`). This follows the spec literally ("sum each period
  column") but is semantically meaningless. Because it's shared and
  spec-ambiguous, it is *not* a ranking differentiator — except in #4, where
  it is compounded by a test asserting the result as correct.
- **`nan`/`inf` acceptance** and **unenforced ROW_ID uniqueness** affect the
  two single-module dict solutions (#3, #4); the winner (#1) is the only one
  that tests duplicate ROW_IDs.
- **The validation stage separated the field.** Its literal spec text is narrow
  ("TOTAL *column* values match the sum of the row's period values"), which
  every solution technically satisfies for category rows — but the *intent*
  (independently verify the rendered output) is met by none. #1 comes closest;
  #2 breaks it into a false-rejection bug; #3 and #4 reduce it to a tautology or
  omit a required check.
- **100% coverage is misleading in every case.** Coverage tracks lines
  executed, not behaviors verified. #2's coverage is padded with monkeypatch
  tests; #1, #3, #4 all reach ~100% while leaving real regressions (padding,
  alignment, fractional values, the enshrined bug) uncaught.

## Accuracy of the pre-existing self-analyses

All four self-analyses are honest and factually accurate on counts, coverage,
and **test-hygiene critiques** (they correctly flag their own tautological,
assertion-free, and monkeypatched tests). **All four miss the substantive
correctness bugs**, however — none identifies its solution's real defect
(false-rejection, circular validation, missing Check #3, or the enshrined
TOTAL-row bug). They are good test-quality reviews but not correctness audits,
and each implicitly over-trusts "all tests pass at 100% coverage."

## Bottom line

`sol-…13-28-18` is the clear winner: correct on every legitimate input, most
idiomatic design, `Decimal` money, and the most thorough error handling.
`sol-…12-57-29` is the best-engineered and best-tested on paper but is dragged
to 2nd by a real bug that makes the pipeline reject its own valid output.
`sol-…13-18-28` and `sol-…13-41-45` share a single-module/dict/float shape and
a weak validation stage; #3 edges out #4 because its core stages are correct and
its tests don't lie, whereas #4 ships an active output bug that a test certifies
as correct and omits a required validation check.
