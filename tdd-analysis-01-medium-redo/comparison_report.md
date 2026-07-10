# Report Pipeline — Solution Comparison

Six solutions to the same task (`task.md`): a 4-stage report pipeline
(**parse → aggregate → format → validate**) plus a full-pipeline runner, each
stage exposed as a separate callable and errors returned as structured values.

Each solution was assessed by a dedicated reviewer on three dimensions —
**design**, **code quality**, and **test effectiveness** — with the test suite
actually executed. This report consolidates and ranks them.

---

## Ranking at a glance

| Rank | Solution | Design | Code | Tests | Overall | Test result | Impl / Test LOC |
|------|----------|:------:|:----:|:-----:|:-------:|-------------|-----------------|
| 🥇 1 | **sol-2026-07-08_12-57-29** | 8 | 8 | 8 | **8.0** | 107 passed | 497 / 881 |
| 🥈 2 | **sol-2026-07-10_17-11-55** | 8 | 8 | 7 | **8.0** | 90 passed | 484 / 850 |
| 🥉 3 | **sol-2026-07-08_13-28-18** | 8 | 8 | 7 | **7.5** | 75 passed | 330 / 430 |
| 4 | **sol-2026-07-10_16-51-18** | 7 | 7 | 6 | **6.5** | 29 passed | 207 / 304 |
| 5 | **sol-2026-07-10_17-04-49** | 6 | 6 | 6 | **6.0** | 62 passed | 348 / 360 |
| 6 | **sol-2026-07-10_16-40-51** | 6 | 6 | 6 | **6.0** | 25 passed | 142 / 228 |

All six suites pass their own tests. The ranking is driven by **spec
correctness**, **robustness of error handling**, and **whether the tests
actually guard the tricky behaviour** — not by test count.

---

## Cross-cutting findings

Two issues recur across almost every solution and are worth calling out because
they explain most of the score differences.

**1. The "TOTAL row mixes headcount into dollars" semantic flaw (5 of 6).**
Every multi-file and most single-file solutions sum `REVENUE + COST + HEADCOUNT`
into a single per-period subtotal and then render it with a `$` prefix — so a
Q1 with REVENUE 1000, COST −200, HEADCOUNT 10 prints a TOTAL of `$810.00`,
adding 10 people to a dollar figure. The spec's wording ("summing each period
column") is genuinely ambiguous, so this is not scored as an outright bug, but
it is nonsensical output and **no solution's tests catch it** — the reviewers'
most consistent test blind-spot.

**2. The output-validation stage is weak nearly everywhere.** The spec asks
validation to independently confirm the table is well-formed (every period
present, TOTAL = sum of period values, no column narrower than its header). In
practice most solutions either re-derive the layout with the same code the
formatter used (so a real formatter bug would pass), do substring matching
instead of column parsing, or implement the width check as a literal no-op /
`pass`. Only `12-57-29` and `17-11-55` genuinely implement the TOTAL-sum check;
the width check is effectively dead in all of them.

The three older/larger multi-module solutions (`12-57-29`, `13-28-18`,
`17-11-55`) also do parse-stage validation properly and several use `Decimal`
for money. The three newer single-file-ish solutions are more compact but two
of them **crash on malformed parse input** instead of returning the structured
error the spec explicitly requires.

---

## Detailed assessments

### 🥇 1. sol-2026-07-08_12-57-29 — Overall 8.0
*Clean, well-decomposed pipeline with the strongest test suite; all 107 tests pass.*

**Strengths**
- One module per stage, each a pure callable, composed by `run_pipeline`; tidy public surface in `__init__.py`. Matches the spec's API shape exactly.
- Structured errors as dataclasses (`ParseError`, `ValidationError`) carrying `stage`, `reason`, and the offending `raw` string.
- Well-documented `AggregatedData` with per-cell / per-period-subtotal / per-category-total / grand-total; correct chronological and category ordering.
- Formatting rules all correct: `$1,234.56`, `-$200.00` (minus outside `$`), headcount as plain int, header-aware column widths, 2-space padding.
- Nicest test suite of the six: negative-COST-allowed vs negative-REVENUE/HEADCOUNT-rejected, all four validation failure modes (via targeted monkeypatching), ordering, and end-to-end error propagation.

**Weaknesses**
- HEADCOUNT summed into monetary subtotals/grand total and rendered as dollars (the cross-cutting flaw #1); unguarded by tests. `aggregate.py:68-79`, `format.py:110-115`.
- Bottom TOTAL row's own TOTAL cell is never validated — corrupting only the grand-total cell passes validation. `validate.py:100-126`.
- `_extract_cells` reads cells by fixed-width position, tightly coupled to the formatter's constants (`validate.py:39-51`); validation is somewhat self-referential.

**Why #1:** highest and most balanced scores (8/8/8), the most thorough and
genuinely meaningful tests, and correct, robust parse/aggregate/format. Edges
out #2 mainly on test depth and cleaner validation.

---

### 🥈 2. sol-2026-07-10_17-11-55 — Overall 8.0
*Clean 4-module pipeline using `Decimal` throughout; 90 tests pass, strong on the tricky rules.*

**Strengths**
- One module per stage plus `run_pipeline`, all re-exported; API shape matches spec.
- `Decimal` end-to-end — best money-precision handling of the group.
- Consistent structured errors (`{stage, input, reason}` / `{stage, reason}`); pipeline short-circuits correctly.
- Thorough, correct parse validation (field count, positive/unique ROW_ID, category whitelist, negative-only-for-COST, strict `^\d{4}-Q[1-4]$` regex).
- Validation checks 1 (all periods present) and 2 (TOTAL = sum, by re-parsing rendered cells) genuinely implemented and exercised by mutation-style tests.

**Weaknesses**
- Validation check 3 ("no column narrower than its header") is dead code — asserts a condition that can never be true by construction (`validate_output.py:191-207`), plus a `pass` no-op block (`:75-92`). The spec's third check is nominally present but cannot fire.
- Same headcount-in-dollars TOTAL mixing as the others (cross-cutting flaw #1).
- `validate_output.py` is over-long and cluttered with leftover exploratory comments/dead code, hurting readability relative to its tidy sibling modules.
- A few trivial format tests assert almost nothing (`test_values_right_aligned` only checks line count; `test_two_spaces_padding` only checks `"  " in line`).

**Why #2:** essentially tied with #1 on design and code (and arguably better on
money handling via `Decimal`), but loses a point on tests — one required
validation check is un-testable dead code and several format tests are weak.

---

### 🥉 3. sol-2026-07-08_13-28-18 — Overall 7.5
*Same clean multi-module shape and `Decimal` usage; slightly thinner tests and one no-op test.*

**Strengths**
- Clean per-stage decomposition, re-exported; `run_pipeline` short-circuits on first failing stage.
- `Decimal` throughout; thorough, correct parse validation (IDs, categories, negative rules, period regex).
- Correct aggregate ordering and all the tricky format rules (`$1,234.56`, `-$200.00`, headcount as int, header-aware widths, padding).
- Mostly meaningful tests: tamper-based validation tests, first-error propagation, negative-cost vs negative-revenue distinction.

**Weaknesses**
- Headcount-in-dollars TOTAL mixing (flaw #1), unguarded by tests. `aggregate.py:58-71`, `format.py:116-121`.
- Validation re-derives layout from `AggregatedData` rather than measuring the actual table string, so it can't detect a genuine formatter width bug; check 3 can essentially never fail (`validate.py:46-47`). Check 1 is a substring test (`period not in header_line`).
- Dead code: `total_col_width` computed but unused (`format.py:78`). One **no-op test** whose body is entirely comments and asserts nothing (`test_format.py:163-176`).
- Minor: `PERIOD_RE` accepts `0000-Q1`; `int()` tolerates surrounding whitespace in ROW_ID.

**Why #3:** design and code quality match the top two, but tests are noticeably
thinner (75 vs 90/107), include a genuine no-op test, and the validation stage
is weaker.

---

### 4. sol-2026-07-10_16-51-18 — Overall 6.5
*Compact, readable 5-module pipeline that handles the happy path well but doesn't defend against malformed input.*

**Strengths**
- Clean minimal decomposition, one callable per stage plus a thin `run_pipeline` orchestrator.
- Well-modeled aggregate structure; correct chronological + category ordering (idiomatic `defaultdict`).
- Core formatting rules verified correct: `$1,234.00`, `-$200.00` (minus outside `$`), headcount as int, right-aligned, header-aware widths, 2-space padding.

**Weaknesses**
- **Crashes on malformed input** instead of returning a structured parse error — `int(parts[0])` / `float(parts[2])` / `parts[3]` are unguarded (`parse.py:11,13`). Spec violation; entirely uncovered by tests.
- ROW_ID "positive unique" constraint never enforced.
- Output validation is substring-based, not structural; the "no column narrower than its header" check is a **no-op** that just re-runs the membership check (`validate.py:53-61`).
- Single test file; no malformed-input tests, so the crash is uncaught. `float` arithmetic rather than `Decimal`. Duplicated `CATEGORIES` constant across three modules.

**Why #4:** cleaner and better-structured than the two below it, but the parse
crash is a real spec violation and the validation stage barely validates.

---

### 5. sol-2026-07-10_17-04-49 — Overall 6.0
*Single-module pipeline with a genuinely correct, thorough parser — undermined by a broken TOTAL row and visible dead scaffolding.*

**Strengths**
- All four stages exposed plus `run_pipeline`; structured `ParseError`/`ValidationError` dataclasses; correct first-failing-stage propagation.
- **Best parser of the single-file solutions** — full validation: field count, non-int/non-positive/duplicate ROW_ID, unknown category, non-decimal value, negative REVENUE/HEADCOUNT rejected while negative COST allowed, strict period regex.
- Correct per-cell formatting and good docstrings; 62 tests pass.

**Weaknesses**
- TOTAL row mixes categories and formats headcount as dollars; a headcount-only report renders the TOTAL row as `$42.00` (flaw #1, and here clearly wrong). `pipeline.py:230`.
- **Dead scaffolding shipped in the code:** a `has_dollar`/`has_headcount` branch immediately overwritten ("Recalculate cleanly", `pipeline.py:216-230`), an `if False else` no-op (`:249`), and computed-but-unused `col_offsets` (`:334`).
- Validation is shallow: period presence via naive `p in table` substring; the width check is an explicit `pass` no-op (`:322-328`).
- Tests never assert the TOTAL row's numeric values, so the mixing bug is undetected.

**Why #5:** its parser is actually stronger than #4's, but it's pulled down by
the broken/meaningless TOTAL output, the shallow validation, and unusually
visible dead code that should never have shipped.

---

### 6. sol-2026-07-10_16-40-51 — Overall 6.0
*The most compact solution (142 impl LOC); gets the happy path right but is the least robust.*

**Strengths**
- Clean 4-stage decomposition in a single file (appropriate for the scope) plus `run_pipeline`.
- Sensible aggregate structure; correct chronological sort and category ordering.
- Formatting core is correct: thousands separators, `-$200.00`, headcount as int, header-aware widths, TOTAL row/column, ≥2-space padding.
- Tests cover all stages and the key parse edge cases (negative COST allowed, negative REVENUE/HEADCOUNT rejected).

**Weaknesses**
- **Parse does no structural validation and crashes** on malformed input (`IndexError`/`ValueError`) rather than returning a structured error — direct spec violation (`pipeline.py:9-13`).
- ROW_ID positivity/uniqueness never checked.
- Validation check 3 is tautological — it re-runs `format_table` and compares strings, so it can never catch a totals-don't-add-up table (`pipeline.py:129-131`); the width check is crude/dead.
- `float` arithmetic throughout; headcount-in-dollars TOTAL mixing; no tests for malformed input, duplicate IDs, or column-width correctness (assertions lean on substring `in`).

**Why #6:** shares the parse-crash spec violation with #4 but is weaker
overall — no ROW_ID checks, the most tautological validation stage, and the
thinnest test suite (25 tests). Impressively compact, but least robust.

---

## Takeaways

- **The multi-module solutions (`12-57-29`, `17-11-55`, `13-28-18`) are the strongest** — better parse validation, `Decimal` money handling, and more genuinely meaningful tests. Decomposition matched the task's four-stage shape naturally.
- **`12-57-29` is the best overall**: balanced 8/8/8, the deepest test suite, and the cleanest validation that actually reuses the formatter's layout.
- **The single-file solutions traded robustness for brevity.** Two of three crash on malformed input — the one behaviour the spec is most explicit about ("return a structured error identifying which input failed and why").
- **Everyone's blind spots are the same two things:** the semantics of the TOTAL row when categories are mixed (headcount summed into dollars), and a real, independent output-validation stage (most are self-referential or contain no-op checks). A stronger submission would (a) decide and test what the TOTAL row means across heterogeneous categories, and (b) validate by parsing the *actual* rendered table rather than re-deriving it from the same data.
