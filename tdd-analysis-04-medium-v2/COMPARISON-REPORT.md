# Comparison Report: Report-Formatting Pipeline (4 Solutions)

Task: a 4-stage Python pipeline — **Parse → Aggregate → Format → Validate** — each stage a
separate callable, plus a full-pipeline function returning either the table string or the
structured error from whichever stage failed (`task.md`).

Each solution was analysed independently (source + tests read in full, tests executed, coverage
measured, spec conformance checked by running the code). Findings were then merged and ranked.

---

## TL;DR ranking

| Rank | Solution | Design | Code | Tests | Tests run | Coverage | Headline weakness |
|------|----------|:------:|:----:|:-----:|:---------:|:--------:|-------------------|
| 🥇 1 | **sol-2026-07-10_10-17-42** | 8 | 8 | 7 | 51 pass | 100% | HEADCOUNT-only TOTAL row printed as `$`; validation is a substring check, not arithmetic |
| 🥈 2 | **sol-2026-07-08_12-57-29** | 8 | 8 | 6 | 107 pass | 100% | Fractional HEADCOUNT → *spurious* ValidationError on valid input; tests lean on monkeypatching |
| 🥉 3 | **sol-2026-07-08_13-28-18** | 8 | 7 | 6 | 75 pass | 100% | `NaN`/`Infinity` crash the pipeline instead of a ParseError; validation re-runs the formatter |
| 4 | **sol-2026-07-10_11-23-40** | 7 | 7 | 6 | 43 pass | 100% | Validation is **tautological** (checks aggregate against itself); width check is only a comment |

All four pass their own suites at 100% line coverage — so **coverage is not a discriminator here**.
The differences are in design fidelity, correctness under edge cases, and whether the tests were
*structured to be able to catch* the bugs that exist.

---

## The theme that separates them: the Validate stage

Stage 4 is where these solutions genuinely diverge, and it's the most revealing part of the task
because it asks each candidate to *check its own output*. Ordered from most to least faithful:

1. **sol-...12-57-29** is the only solution whose validator **independently re-parses the rendered
   table string** and compares the extracted numbers — i.e. it actually validates the artifact the
   spec says to validate. Ironically this rigor is what surfaced its own bug (below), but the
   design is the most spec-honest of the four.
2. **sol-...13-28-18** re-derives column geometry by *calling the formatter's own helpers* and
   reparses the string. Real string inspection, but not independent — a shared layout bug would
   pass both.
3. **sol-...10-17-42** inspects the rendered string but only checks that the expected total *string
   appears somewhere on the row* — demonstrably foolable (a corrupted TOTAL column passes as long
   as the same substring occurs in any period column).
4. **sol-...11-23-40** never inspects the table at all — it re-computes totals from
   `AggregatedData` and compares them against `AggregatedData`. Since `aggregate()` always produces
   self-consistent data, the check **can never fail on a real pipeline run** (verified: a table
   rendered with wrong numbers passes validation). The spec's "no column narrower than its header"
   check is also absent — replaced by a comment saying it "relies on format_table being correct."

A related shared observation: the "column narrower than header" check is structurally impossible to
violate in solutions 1, 3, and 4 because widths are computed as `max(header, cell)`. That makes the
missing explicit check harmless in practice, but it's still a literal spec gap in 3 and 4.

---

## Per-solution detail

### 🥇 1st — sol-2026-07-10_10-17-42  (Design 8 · Code 8 · Tests 7)

**Structure.** The most granular decomposition of the four: `models.py` (dataclasses),
`parse.py`, `aggregate.py`, `formatting.py` (shared value formatter), `format_stage.py`,
`validate_stage.py`, `pipeline.py`, all re-exported from `__init__.py`. Errors-as-values,
`Decimal` throughout.

**Why it wins.** Cleanest separation of concerns, the shared `format_value` helper is reused by
both format and validate (good DRY), all five callables exposed at package top level, and the
`AggregatedData` model carries ordered periods/categories plus all three total varieties. Its
51-test suite is the most consistently *behavioural* — parse tests assert exact field values and
error reasons, aggregate tests verify all three totals arithmetically, and alignment is checked by
locating real header-token positions rather than by substring presence.

**Real defects.**
- *(medium)* The TOTAL row hard-codes `$` formatting (`format_stage.py:47-51`): a HEADCOUNT-only
  table prints `$10.00` in its TOTAL row while the data rows show plain integers — an internally
  inconsistent, visibly wrong output.
- *(medium)* `validate_output` checks the TOTAL column with a substring-presence test, not
  arithmetic (`validate_stage.py:44-46`) — verified foolable.
- *(low)* `PipelineError.stage` can never be `"validate"` because `format_table` calls
  `validate_output` internally, so validation failures are mislabelled `stage="format"`.
- *(low)* Duplicate ROW_IDs not rejected; minor dead imports (`pytest`, `field`).

**Verdict.** The best-engineered candidate; loses points only for subtle correctness issues its
otherwise-strong tests didn't exercise (no HEADCOUNT-only TOTAL test, no arithmetic validation
test).

### 🥈 2nd — sol-2026-07-08_12-57-29  (Design 8 · Code 8 · Tests 6)

**Structure.** Textbook 5-module package (`parse`/`aggregate`/`format`/`validate`/`pipeline`) with
a re-exporting `__init__`. Dataclasses for rows and errors, layout logic factored into a shared
`compute_layout` used by both format and validate. **107 tests** — the broadest suite.

**Why it's this high.** Excellent readability and documentation, the strongest `AggregatedData`
model, and the **only genuinely independent validation stage** (re-parses the rendered table).
Systematic parse-error coverage (every ROW_ID form, casing, negative REVENUE/HEADCOUNT, all period
violations) with real end-to-end tests and no mocking on the happy paths.

**Real defects.**
- *(medium)* **Fractional HEADCOUNT yields a spurious `ValidationError` on valid input.**
  `_fmt_headcount` rounds each cell independently, but validate reparses the rendered integers and
  compares their sum to the rendered TOTAL. Input `["1:HEADCOUNT:0.5:2024-Q1","2:HEADCOUNT:0.5:2024-Q2"]`
  renders each cell as `0` (banker's rounding) but the TOTAL as `1`, so the pipeline *rejects
  legitimate input*. The spec permits decimal VALUEs with no integrality constraint on HEADCOUNT.
- *(low)* Validation never checks the TOTAL row's own grand total (only the category rows).
- *(low)* `inf`/`nan`/`1_0` accepted by parse.

**Test caveat.** Its headline 100% coverage is reached partly by **monkeypatching private
internals** (`compute_layout`, `_extract_cells`, `_parse_number`) to hit defensive branches that
real input can't reach — brittle, and it masks rather than exposes the fractional-headcount bug.
One alignment test (`endswith(rstrip())`) is near-tautological.

**Verdict.** The most spec-faithful validation and the broadest tests, dragged to 2nd by a bug that
rejects valid input and by coverage that's partly manufactured through internal mocking. Genuinely
close to 1st.

### 🥉 3rd — sol-2026-07-08_13-28-18  (Design 8 · Code 7 · Tests 6)

**Structure.** Clean 5-module package, `Decimal` money math, union-typed structured errors.
75 tests, 100% coverage.

**Real defects.**
- *(medium)* **`NaN`/`Infinity` crash the pipeline** with an uncaught `InvalidOperation` instead of
  returning a `ParseError` — `Decimal("NaN")` constructs fine, then `value < 0` raises. Directly
  violates "parse … return a structured error identifying which input string failed."
- *(medium)* Mixed money+headcount TOTAL renders a meaningless `$8,005.00` (headcount summed into a
  currency total); validation can't detect it because the bogus subtotal is self-consistent.
- Validation re-invokes the formatter's own layout helpers rather than checking numerically, and
  `format.py` leaks two public helpers that exist only for `validate`.

**Test caveat.** Contains an **assertion-free test** (`test_format_column_widths_at_least_header_width`
is just a comment), several vacuous `isinstance(result, (str, ValidationError))` assertions, a
conditionally-skipped tamper test, and a mock-driven branch to reach a check that real output can't
trigger. No test asserts a full expected table string — which is why both real bugs slip through.

**Verdict.** Sound structure and error model, but two genuine correctness defects (a crash and a
nonsensical total) escape a suite that never pins exact output.

### 4th — sol-2026-07-10_11-23-40  (Design 7 · Code 7 · Tests 6)

**Structure.** Everything in a single `pipeline.py` (299 lines). Functions are separate but not
modules — against the decomposition spirit of "expose each stage as a separate callable." 43 tests,
100% coverage.

**Real defects.**
- *(medium-high)* **Validation is tautological.** `validate_output` re-derives totals from
  `AggregatedData` and compares them to `AggregatedData` — it never inspects the rendered table.
  Verified: a table rendered with wrong numbers passes validation unchanged. The spec's core stage-4
  guarantee is effectively absent.
- *(medium)* The "no column narrower than its header" check is not implemented — only a comment.
- *(medium)* Mixed-category TOTAL sums headcount into a dollar total (`$810.00`), unguarded except
  for the HEADCOUNT-only case.
- *(low)* Duplicate ROW_IDs not enforced; hand-written `__init__` on dataclasses defeats
  `@dataclass`; triplicated negative-money formatting; broad `except Exception` for Decimal parse;
  no docstrings on the main stage functions.

**Test caveat.** No test for `ValidationError` propagating through `run_pipeline` (a whole error
path of the top-level function is untested); validate tests inject inconsistent `AggregatedData`
that the real pipeline can never produce (false confidence); a near-tautological width test.

**Verdict.** Well-formed and fully passing, but the validation stage — the differentiating part of
this task — does essentially nothing real, and two of the four required stage-4 checks are missing.
Coverage flatters it.

---

## Cross-cutting notes

- **Shared spec ambiguity (not counted heavily against anyone):** the TOTAL row sums each *period
  column* across categories, so mixing units (dollars + headcount) into one column total is what
  the spec literally asks for. The clearly-wrong variant is only the *formatting* of a
  HEADCOUNT-only TOTAL as `$` (sol-...10-17-42) — sol-...11-23-40 actually handles that specific
  case correctly via its `== ["HEADCOUNT"]` guard.
- **100% coverage everywhere ≠ correctness.** Every suite hits 100% lines yet each solution ships
  at least one real bug. In three of four cases the bug survives *because* the tests never assert on
  a full rendered table and/or reach branches only via mocking. The single most valuable missing
  test across the board is a **golden/snapshot assertion of an exact expected table string**.
- **Every pre-existing self-analysis was overconfident about correctness.** All four honestly
  discuss test hygiene but none identified the actual correctness bug in their own solution;
  sol-...11-23-40's notes even call the solution "correct" while its validation is tautological.

## Recommendation

Adopt **sol-2026-07-10_10-17-42** as the base for its cleanest architecture and strongest tests,
then graft in **sol-2026-07-08_12-57-29**'s independent (string-reparsing) validation approach —
while fixing that solution's per-cell headcount rounding so fractional headcounts don't trigger a
false ValidationError. That combination gives the best design *and* a validation stage that
actually does its job.
