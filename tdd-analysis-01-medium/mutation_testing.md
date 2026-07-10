# Mutation Testing Report

Tool: [`mutmut`](https://mutmut.readthedocs.io/) v3.6.0, run with `mutmut run` inside a per-project `.venv`, mutating only `report_pipeline/` (test files excluded). See [`README.md`](README.md) for setup notes.

## Ranking (best → worst mutation coverage)

| Rank | Codebase | TDD | Total | Killed | Survived | Score |
|---|---|---|---|---|---|---|
| 1 | `sol-2026-07-08_12-57-29/` | No | 318 | 285 | 33 | **89.6%** |
| 2 | `sol-2026-07-08_13-28-18/` | No | 386 | 325 | 61 | **84.2%** |
| 3 | `sol-2026-07-08_13-18-28/` | Yes | 342 | 277 | 65 | **81.0%** |
| 4 | `sol-2026-07-08_13-41-45/` | Yes | 361 | 279 | 82 | **77.3%** |

Both non-TDD runs beat both TDD runs on mutation score, the same direction as [`comparison-report.md`](comparison-report.md)'s ranking. Sample size is 2-vs-2, so treat this as a weak, suggestive signal rather than a proof — but it's a second, independent metric (mutation coverage, not LLM-judged quality) pointing the same way. See [`tdd-correlation.md`](tdd-correlation.md) for the existing discussion of *why* that might be.

---

## Cross-cutting patterns (present in all four codebases)

The same handful of gap shapes recur everywhere, almost identically, regardless of TDD/non-TDD. This strongly suggests they're artifacts of *how these tests are typically written* rather than something either workflow specifically caused:

1. **Substring assertions on error messages instead of exact matches.** Every codebase builds error/validation results as dicts or objects with a `reason` (and often a `raw`/`input` echo of the offending value). Tests almost always check `isinstance(...)` or `"foo" in result.reason`, never the exact string or the full key set. This lets mutmut freely rename dict keys (`"reason"` → `"REASON"`), swap `raw=line` → `raw=None`, or case-flip/mark message text, and survive undetected. This is the single largest gap cluster in every project (roughly 40-60% of all survivors).
2. **Zero/boundary values are never tried.** `value < 0` checks, `>= 0` sign-formatting branches, and tolerance comparisons (`> 0.005`, `> 0.01`) are tested with comfortably-negative or comfortably-large inputs, never the boundary itself (`0`, or the exact tolerance value). This turns `<` vs `<=` and `> X` vs `>= X` mutants into permanent survivors.
3. **`.get(key, default)` fallback branches are dead code under test.** All four projects build lookup tables (by period/category) from the same data they later read back from, so the "key is missing" branch of a defensive `.get(..., 0.0)` is never actually exercised. Mutating the default value or the fallback dict has no observable effect.
4. **Table-rendering alignment/padding is checked by substring, not by position.** Tests assert things like `"TOTAL" in header_line` or "no trailing whitespace at end of line" rather than exact column content. This blinds every project's suite to `ljust`↔`rjust` swaps, padding-width changes, and header-label mutations.
5. **The custom chronological period-sort key is an effectively equivalent mutant everywhere.** Because periods are always `YYYY-QN` with a single-digit quarter, lexicographic string sort and the intended `(year, quarter)` numeric sort always agree on this input domain. All four projects have `key=_period_sort_key` survive when deleted or replaced with `None`. This isn't a real test gap so much as unfalsifiable code given the current input format.

---

## Rank 1 — `sol-2026-07-08_12-57-29/` (No TDD) — 89.6%

**By file:**

| File | Mutants | Killed | Survived | Score |
|---|---|---|---|---|
| `pipeline.py` | 11 | 11 | 0 | 100% |
| `aggregate.py` | 48 | 46 | 2 | 95.8% |
| `parse.py` | 68 | 61 | 7 | 89.7% |
| `validate.py` | 81 | 71 | 10 | 87.7% |
| `format.py` | 110 | 96 | 14 | 87.3% |

**Gaps:**
- **`ParseError.raw` unasserted on 5 of 7 error paths** (`parse.py:51-100`) — only 2 of the 7 places `parse()` builds a `ParseError` have their `.raw` field checked by a test; the other 5 (bad ROW_ID, non-positive ROW_ID, duplicate ROW_ID, bad VALUE, bad PERIOD) only check `.reason` or `isinstance`.
- **Zero boundary on REVENUE/HEADCOUNT non-negativity** (`parse.py:85`) — the only zero-value test uses `COST`, which is exempt from the check, so `value < 0` vs `<= 0` vs `< 1` are indistinguishable.
- **Dead defensive branch** `label_width < 0` (`validate.py:94-95`) — unreachable via any real code path (`label_width` is a `max()` over string lengths, always ≥ 0); the one test that reaches it does so via monkeypatching and only substring-checks the message.
- **Float-tolerance boundary untested** (`validate.py:119`, `> 0.005`) — existing mismatch test is off by $699, far outside the tolerance window, so `>` vs `>=` at exactly `0.005` is unverified.
- **`_parse_number`'s negative-sign slicing only tested via `-$` shape** (`validate.py:26-30`) — a mutant that drops 2 chars instead of 1 happens to be "accidentally correct" for `-$200.00` but would silently mis-parse a bare `-42`, a shape no test exercises.
- **`compute_layout` TOTAL-row dict keys/`_fmt_value(cat=None)` swaps** (`format.py:18-34`) — survive because no fixture makes the TOTAL row (as opposed to a category row) the width-determining cell for any column.
- **Alignment/header-label exactness** (`format.py:92,98`) — `.rjust`→`.ljust` and header-label `""`→`"XXXX"` survive because the alignment test only checks "no trailing whitespace," not per-column position.
- **Dead code:** `periods = aggregated.periods` in `format_table` (`format.py:84`) is an unused local — not a test gap, just dead code to delete.
- **Equivalent mutant:** `_period_sort_key` removal (`aggregate.py:54`) — see cross-cutting pattern #5.

**Takeaway:** `pipeline.py` (orchestration) is airtight. The remaining gaps are concentrated in exact-string/exact-position assertions and a couple of genuinely dead/unreachable branches — the *logic* itself is thoroughly covered.

---

## Rank 2 — `sol-2026-07-08_13-28-18/` (No TDD) — 84.2%

**By file:**

| File | Mutants | Killed | Survived | Score |
|---|---|---|---|---|
| `pipeline.py` | 11 | 11 | 0 | 100% |
| `aggregate.py` | 55 | 51 | 4 | 92.7% |
| `parse.py` | 70 | 60 | 10 | 85.7% |
| `validate.py` | 107 | 89 | 18 | 83.2% |
| `format.py` | 143 | 114 | 29 | 79.7% |

`format.py` is this project's weakest file both in absolute survivor count (29) and score — the largest single weak spot across all four codebases.

**Gaps:**
- **Error-payload fields checked inconsistently** (`parse.py:46-75`, `validate.py:30-42`) — `.raw` asserted on only 2 of 8 parse-error branches; `validate_output`'s empty-table/no-TOTAL-column checks never inspect `.reason` content at all.
- **`.get(key, default)` fallbacks in `aggregate.py:61,68` and `format.py:50,60,109,111`** — every test grid is fully populated, so the missing-key fallback path in `period_subtotals`/`category_totals`/`_compute_col_widths` is never taken. The one existing test that builds a partial grid (`test_aggregate_missing_cell_not_in_dict`) checks the *dict membership*, not the downstream *sum*.
- **Label-column alignment** (`format.py:127-134`) — `ljust`/`rjust` swap on column 0 (labels) vs. other columns survives because all label strings in test fixtures happen to fit exactly, so the justification direction has no visible effect.
- **`all_headcount` flag mutations** (`format.py:39`) — `==`→`!=`, string case/marker swaps all survive because no test uses a *mixed* category set (REVENUE + HEADCOUNT together) to prove the flag is correctly `False` in that case; only the all-true and (implicitly) all-false paths are separately exercised.
- **Zero-boundary values** — same pattern as rank 1, in `parse.py:65` (REVENUE/HEADCOUNT `< 0`), `format.py:24` (`_fmt_dollar`, `< 0`), `validate.py:81` (`> Decimal("0.005")`), and `validate.py:95` (`_get_field`'s `col_start >= len(line)` boundary).
- **Equivalent mutant:** period sort key (`aggregate.py:33-52`) — same as cross-cutting #5.
- **Residual cosmetic literals** (`~10` survivors) — `""`/`"TOTAL"` placeholder swaps in header construction that are only partially checked elsewhere; a single full-table snapshot test would close most of these at once.

**Takeaway:** Similar profile to rank 1 but the gaps are wider — particularly the `.get()` fallback and alignment clusters in `format.py` — consistent with a somewhat less exhaustive test suite for the formatting layer specifically.

---

## Rank 3 — `sol-2026-07-08_13-18-28/` (TDD) — 81.0%

Structurally different from the other three: this solution keeps everything in one file, `pipeline.py` (all of `parse`/`aggregate`/`format_table`/`validate_output`/`run_pipeline` live there), with tests nested at `report_pipeline/tests/` rather than a top-level `tests/` dir.

**By function:**

| Function | Survived / Total | Score |
|---|---|---|
| `_period_sort_key` | 0 / 7 | 100% |
| `_valid_period` | 0 / 8 | 100% |
| `run_pipeline` | 1 / 15 | 93.3% |
| `aggregate` | 2 / 44 | 95.5% |
| `_fmt_money` | 2 / 4 | 50% |
| `validate_output` | 14 / 51 | 72.5% |
| `parse` | 21 / 94 | 77.7% |
| `format_table` | 25 / 127 | 80.3% |

**Gaps:**
- **Error-message content never asserted precisely** (`parse` lines 15,24,28,34,37,41; `validate_output` lines 158,165,173,184) — the single largest cluster here (~35 survivors). Tests check `result["error"]` and sometimes a substring of `result["reason"]`, but substring checks are weak enough that mutmut's `XX...XX`-wrapped text still contains the checked substring (e.g. `"XXinvalid row_idXX"` still contains `"row_id"`). Dict-key renames are invisible because no test iterates or asserts the key set.
- **`.get(key, default)` fallbacks in `format_table`** (lines 106,108,113) — same shape as ranks 1-2: every test-built `aggregated` object has every referenced key present, so the fallback default and even the lookup key itself can be swapped for `None`/`1.0`/dropped without effect. A sparse-aggregate test (a period missing one category) would kill ~14 mutants at once.
- **Redundant boolean condition** in row-selection (`format_table` lines 99-100, `c in category_totals or any(...)`) — `or`↔`and` and `in`↔`not in` flips survive because, given how `aggregate()` actually builds its output, both clauses are always co-true/co-false. Only reachable by hand-crafting an inconsistent `aggregated` object and calling `format_table` directly.
- **Layout constants** (`label_width`/`padding`/`rjust`/separator on lines 126,129,136,137,141) — none are pinned down by an exact full-line assertion; existing layout test (`test_format_table_column_not_narrower_than_header`) is effectively tautological.
- **Zero-boundary values** — `parse` line 36 (`value < 0` for REVENUE/HEADCOUNT) and `_fmt_money` line 191 (`value < 0`), same shape as the other projects: no test ever uses exactly `0`.
- **Equivalent mutants:** period-sort key (line 60) and `run_pipeline`'s `isinstance(...) and "error" in parsed` (line 205, `and`→`or` survives because `parse()`'s contract makes both operands always co-true/co-false) — neither is killable without changing the input domain or `parse()`'s contract.
- One survivor (`_fmt_value`/HEADCOUNT `str(int(round(value)))` → `str(None)`, mutant `_16`) looked like it *should* be caught by an existing assertion and is flagged in the sub-analysis as needing re-verification rather than a confirmed gap.

**Takeaway:** `_period_sort_key` and `_valid_period` are fully covered, and `run_pipeline`/`aggregate` are very strong. The weak spot is squarely the error-message/exact-string-content discipline and the formatting layer's untested fallback/layout paths — the same shape as the non-TDD projects, just wider.

---

## Rank 4 — `sol-2026-07-08_13-41-45/` (TDD) — 77.3%

Also single-file (`pipeline.py`), same shape of codebase as rank 3.

**By function:**

| Function | Survived / Total | Score |
|---|---|---|
| `aggregate` | 0 / 41 | 100% |
| `run_pipeline` | 0 / 10 | 100% |
| `_fmt_value` | 2 / 9 | 77.8% |
| `format_table` | 26 / 114 | 77.2% |
| `validate_output` | 20 / 73 | 72.6% |
| `parse` | 27 / 94 | 71.3% |
| `_parse_monetary` | 7 / 20 | **65.0%** (weakest function of all four codebases) |

**Gaps:**
- **Error-payload dict-key/string mutations** (`parse` lines 19-37, `validate_output` lines 180,196,220) — the largest cluster (~50 survivors), identical pattern to rank 3: loose substring checks (`"category" in result["reason"]`) don't catch dict-key renames or full message-text mutation.
- **`_parse_monetary` has essentially no direct unit test** (lines 167-173) — it's only exercised indirectly through `validate_output`'s round-trip (parse output formatted by `format_table`, then re-parsed), so inputs are always well-formed. Notably, mutant `_20` (`return -val if negative else val` → `return +val if negative else val`, i.e. an actual **sign-inversion bug**) survives — this is the one finding across all four projects that looks closest to a real latent-bug risk rather than a purely cosmetic gap, because the round-trip nature of the only test coverage means a wrong-sign parse could plausibly still pass validation in some cases. Recommend a direct test: `_parse_monetary("-$200.00") == -200.0`.
- **Zero/negative boundary at cell and aggregate-row level** (`parse` line 33, `_fmt_value` line 90, and `format_table`'s `period_total_cell`/`grand_total_cell` lines 125,129 `>= 0` checks) — no fixture ever sums to exactly `0.00`, and no fixture produces a genuinely negative period/grand total, so the `-$` rendering branch is barely exercised at all.
- **`.get(key, default)` fallbacks in `format_table`** (lines 105-107,114,118,124) — same shape as every other project.
- **`continue` vs `break` in `validate_output`'s row-skip loop** (lines 202-216) — a real test-design gap: all three skip-branch tests place the skippable row *last* in the table, so `continue` (keep checking subsequent rows) and `break` (stop entirely) are indistinguishable. A skippable row placed in the *middle*, followed by a deliberately-corrupted TOTAL row, would catch all three mutants at once — and is the clearest concrete "add this one test" recommendation across the whole report.
- **Off-by-one on `len(cells) < 2` and the `0.01` mismatch tolerance** (lines 206,217) — same boundary-value gap shape as elsewhere, just never at the exact threshold.
- **Header/layout cosmetics** (lines 133,144,149,158) — same shape as the other three projects; one flagged as a possible false-positive/no-op mutant (`col_widths = [0]*n` → `[1]*n`, likely equivalent since `max()` absorbs it).

**Takeaway:** `aggregate` and `run_pipeline` are fully covered, but this project has the widest gaps in `parse`, `validate_output`, and especially `_parse_monetary` — including the one mutant across all four projects that plausibly represents a genuine latent bug rather than a cosmetic/equivalent-mutant gap (the sign-inversion in `_parse_monetary`).

---

## Overall observations

- **No project has any actual failing behavior** — every survivor is either (a) a message/formatting-text exactness gap, (b) a boundary value (zero, exact tolerance) nobody tried, (c) a defensive/fallback branch that's dead code under the test suite's data shapes, or (d) an equivalent mutant (period-sort key, a couple of redundant boolean guards). Rank 4's `_parse_monetary` sign-inversion survivor is the closest thing to a real risk, and even that is only reachable through malformed/edge-case monetary strings.
- **The same fix recipe would raise every project's score substantially**: (1) assert exact error-message text and full key sets instead of substring/`isinstance` checks, (2) add one zero-value and one exact-tolerance-boundary test per numeric check, (3) add one sparse/partial-grid fixture to exercise `.get()` fallbacks, (4) add one exact full-line string assertion to pin down table layout instead of substring checks.
- **Non-TDD outscored TDD on mutation coverage in this sample**, mirroring the LLM-judged quality ranking in [`comparison-report.md`](comparison-report.md). The gap shapes are nearly identical across all four, though — this looks more like "these are all similarly-styled test suites with the same blind spots" than "TDD produced categorically different tests." Worth treating as a data point for [`tdd-correlation.md`](tdd-correlation.md) rather than a standalone conclusion.

=================

> I see there are concerns like checking for substrings instead of full strings, that survive the mutation. I wonder if there's a trade-off here between full coverage versus brittleness of tests? Because testing for full strings usually makes tests more brittle? What is your opinion?

Yes, it's a real tradeoff, but I don't think the fix is "make every assertion exact." My take: split it by what the string actually represents.

- Structural bits (dict keys, error codes/types, which field is populated) are cheap to pin down exactly and rarely change — assert set(result.keys()) == {"error", "input", "reason"} costs little and catches real contract breaks like a "reason" → "REASON" typo.
- Human-readable prose (the actual message text) is exactly where brittleness bites — if you assert the literal sentence, every wording tweak breaks tests for no safety benefit. Loose substring checks are the right call there; mutmut flagging those as survivors is arguably a false signal, not a real gap. Or, better in the long run: test error codes/types rather than message strings at all, so the prose is free to change.
- Table-rendering output is different — the exact formatting is the behavior under test, so one or two "golden" exact-string tests per rendering function are appropriate and worth the brittleness, while you don't need every variation tested that precisely.

So I wouldn't chase 100% mutation score by exact-stringing everything. I'd treat the report's "error message" survivors as mostly acceptable, and prioritize the other clusters instead (zero-boundary values, .get() fallback branches, the _parse_monetary sign-inversion) — those are catching real logic gaps, not a testing-style tradeoff.