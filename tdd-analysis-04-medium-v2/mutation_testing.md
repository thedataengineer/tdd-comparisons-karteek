# Mutation Testing Report

Tool: [`mutmut`](https://mutmut.readthedocs.io/) v3.6.0, run with `mutmut run` inside a per-project `.venv`, mutating only `report_pipeline/` (test files excluded). See [`README.md`](README.md) for setup notes.

Two of the four codebases here (`sol-2026-07-08_12-57-29` / NT1 and `sol-2026-07-08_13-28-18` / NT2) are byte-identical (source + tests, confirmed via `diff -rq`) to codebases already mutation-tested in the sibling `tdd-analysis-01` folder. Re-running `mutmut` against them here reproduced the exact same total/killed/survived counts, so the gap analysis below for those two is carried over (and re-verified) from that prior run rather than re-derived from scratch.

## Ranking (best → worst mutation coverage)

| Rank | TDD | ID | Codebase | Total | Killed | Survived | Score |
|---|---|---|---|---|---|---|---|
| 1 | Yes | T1 | `sol-2026-07-10_10-17-42/` | 296 | 267 | 29 | **90.2%** |
| 2 | No | NT1 | `sol-2026-07-08_12-57-29/` | 318 | 285 | 33 | **89.6%** |
| 3 | No | NT2 | `sol-2026-07-08_13-28-18/` | 386 | 325 | 61 | **84.2%** |
| 4 | Yes | T2 | `sol-2026-07-10_11-23-40/` | 318 | 258 | 60 | **81.1%** |

This exactly matches the LLM-judged [Quality Ranking](README.md#quality-ranking) in this batch's `README.md` (T1 > NT1 > NT2 > T2) — a second, independent metric agreeing with the first. This is notable in light of `tdd-analysis-01`: there, both non-TDD runs beat both TDD runs on mutation score and LLM-judged quality. Here, T1 was built with the *expanded* TDD instruction prompt (see [`TDD-PROMPT-ANALYSIS.md`](TDD-PROMPT-ANALYSIS.md)) and comes out on top on both metrics, while T2 — built with the same expanded prompt but a much shorter, cheaper session — lands last. That's some evidence the earlier TDD-prompt weaknesses were fixable, but also that TDD alone doesn't guarantee a good result; how thoroughly the session is actually run still dominates.

---

## Cross-cutting patterns (present in all four codebases, regardless of TDD/non-TDD)

1. **Substring assertions on error messages instead of exact matches.** Every codebase builds error/validation results as objects with a `reason` (and often a `raw`/`input_string` echo of the offending value). Tests almost always check `isinstance(...)` or `"foo" in result.reason`, never the exact string or full field set. This lets mutmut freely case-flip message text, mark it with `XX...XX`, or null out an echoed input field, and survive undetected. This is the single largest gap cluster in every project (roughly 30-60% of all survivors).
2. **Zero/boundary values are never tried.** `value < 0` sign checks and `_period_sort_key`-adjacent boundaries are tested with comfortably-negative or comfortably-large inputs, never the boundary itself (exactly `0`). This turns `<` vs `<=`/`< 1` mutants into permanent survivors — and this is the one pattern that recurs as a **flagged, closest-to-real-risk finding in every single codebase this round** (see below).
3. **`.get(key, default)` fallback branches are dead code under test.** All four projects build lookup tables (by period/category) from the same data they later read back from, so the "key is missing" branch of a defensive `.get(..., 0)` is never actually exercised by realistic fixtures. Mutating the default value or dropping the explicit `sum(..., start)` argument has no observable effect.
4. **Table-rendering alignment/padding is checked by substring or "at least N spaces," not by exact position.** This blinds every project's suite to `ljust`↔`rjust` swaps, padding-width changes (`2` spaces → `3` still contains a 2-space substring), and header-label mutations. T2's `cell.rjust(w)` → `.ljust(w)` surviving is the cleanest example — a real, user-visible misalignment defect that no test would catch if introduced for real.
5. **The custom chronological period-sort key is an effectively equivalent mutant everywhere.** Because periods are always `YYYY-QN` with a single-digit quarter and 4-digit year (enforced by each project's own period-validation regex), lexicographic string sort and the intended `(year, quarter)` numeric sort always agree on any input that can actually reach the sort call. All four projects have this sort key survive when deleted, `None`-ed, or have its internal tuple construction mutated. Not a real test gap — the code is unfalsifiable given the current input domain.
6. **Every codebase's "closest to a real bug" survivor this round is the same shape: an unguarded zero-value boundary that's realistic, not contrived.** T1 has *two* independent instances of it (parse-time and format-time); T2 has one at parse time. None of these are currently wrong — they're all currently-correct code with no test pinning the boundary down, so a plausible future "off-by-one" fix (`<` → `<=`, thinking "non-positive") would silently start rejecting/misrendering legitimate `$0.00`/zero-headcount data.

---

## Rank 1 — `sol-2026-07-10_10-17-42/` (T1, TDD) — 90.2%

**By file:**

| File | Mutants | Killed | Survived | Score |
|---|---|---|---|---|
| `pipeline.py` | 18 | 18 | 0 | 100% |
| `aggregate.py` | 61 | 55 | 6 | 90.2% |
| `formatting.py` | 11 | 9 | 2 | 81.8% |
| `validate_stage.py` | 30 | 25 | 5 | 83.3% |
| `parse.py` | 79 | 70 | 9 | 88.6% |
| `format_stage.py` | 97 | 90 | 7 | 92.8% |

**Flagged — closest to real risk:**
- **Zero-value REVENUE/HEADCOUNT boundary untested at parse time** (`parse.py:40`, `x_parse__mutmut_37`/`_38`, `value < 0` → `<= 0`/`< 1`) — current code correctly allows `value == 0`, but no test ever parses a zero-value REVENUE/HEADCOUNT row, so a plausible off-by-one regression would start rejecting completely normal $0 revenue/zero-headcount input.
- **The same boundary shape recurs independently in the formatter's sign logic** (`formatting.py:15`, `x_format_value__mutmut_7`/`_8`, `negative = value < 0` → `<= 0`/`< 1`) — directly reachable via `aggregate.py:41`'s explicit zero-fill of missing period×category cells (which *is* tested for existence, but never checked downstream for correct sign rendering). Two independent instances of the exact same gap shape is a stronger signal than one.

**Gaps:**
- **Error-message text asserted only via substring** (`parse.py:21`, `validate_stage.py:22,35`) — same pattern as every other project; e.g. `"table is empty"` mutated to `"XXtable is emptyXX"` still contains the substring `"empty"` the test checks for.
- **`format_value`'s `category` argument is a no-op for anything but the literal `"HEADCOUNT"`** (`format_stage.py:36-38,51`) — the TOTAL row is rendered by passing a hardcoded category string purely to select a formatting branch; any other string (`None`, wrong case, wrong text) produces identical output, so the literal is unfalsifiable by any test that only checks rendered values. **This is the same design flaw behind this codebase's already-known headline weakness** in the [Quality Ranking](README.md#quality-ranking) table ("HEADCOUNT-only TOTAL row printed as `$`") — the mutation survivors are pointing at the exact same fragile sentinel-string mechanism that produced that bug, from a different angle.
- **Q4 quarter never exercised through `parse()`** (`parse.py:62`, `_valid_period`) — `test_aggregate.py` uses `"2023-Q4"` extensively but only via directly-constructed `ParsedRow` objects, bypassing `parse()`/`_valid_period()` entirely, so the `"-Q4"` literal itself can be mutated undetected.
- **`ParseError.input_string` unasserted on 3 of 4 error paths** (`parse.py:27,38,48`) — the pattern of asserting the echoed input string exists for the invalid-CATEGORY path but wasn't extended to ROW_ID/VALUE/PERIOD error paths.
- **Header row's label column content unchecked** (`format_stage.py:78`) — no test asserts the header row's leading label cell is blank.
- **Minor latent trap, not currently reachable**: `validate_stage.py:42`'s `continue`→`break` mutant only escapes detection via a non-canonical table shape that `format_table()` itself never produces — a real gap in `validate_output`'s own unit tests (which never test line-insertion tampering) but not exploitable through the actual pipeline today.
- **Equivalent mutants:** period-sort key removal/internal mutation (`aggregate.py:31` and the `_period_sort_key` helper itself) and `sum(..., Decimal("0"))`→`sum(...)` dropped explicit start (`aggregate.py:45,55`) — see cross-cutting pattern #5/#3.

**Takeaway:** `run_pipeline`-equivalent `pipeline.py` is airtight (100%), and this is the best-scoring codebase in the batch. Its distinguishing weak spot — the sentinel-category-string branch in `format_value` — is a genuine design smell (not just a test gap) that directly explains this codebase's known TOTAL-row rendering bug.

---

## Rank 2 — `sol-2026-07-08_12-57-29/` (NT1, no TDD) — 89.6%

*Carried over from `tdd-analysis-01`'s analysis of this same codebase; re-verified here with an identical `mutmut run` (318/285/33, exact match).*

**By file:**

| File | Mutants | Killed | Survived | Score |
|---|---|---|---|---|
| `pipeline.py` | 11 | 11 | 0 | 100% |
| `aggregate.py` | 48 | 46 | 2 | 95.8% |
| `parse.py` | 68 | 61 | 7 | 89.7% |
| `validate.py` | 81 | 71 | 10 | 87.7% |
| `format.py` | 110 | 96 | 14 | 87.3% |

**Gaps:**
- **`ParseError.raw` unasserted on 5 of 7 error paths** (`parse.py:51-100`) — only 2 of the 7 places `parse()` builds a `ParseError` have their `.raw` field checked by a test.
- **Zero boundary on REVENUE/HEADCOUNT non-negativity** (`parse.py:85`) — the only zero-value test uses `COST`, which is exempt from the check, so `value < 0` vs `<= 0` vs `< 1` are indistinguishable. (Same cross-cutting pattern #2/#6 as T1 above.)
- **Dead defensive branch** `label_width < 0` (`validate.py:94-95`) — unreachable via any real code path; the one test that reaches it does so via monkeypatching and only substring-checks the message.
- **Float-tolerance boundary untested** (`validate.py:119`, `> 0.005`) — existing mismatch test is off by $699, far outside the tolerance window.
- **`_parse_number`'s negative-sign slicing only tested via `-$` shape** (`validate.py:26-30`) — a mutant that drops 2 chars instead of 1 happens to be "accidentally correct" for `-$200.00` but would silently mis-parse a bare `-42`.
- **`compute_layout` TOTAL-row dict keys/`_fmt_value(cat=None)` swaps** (`format.py:18-34`) — survive because no fixture makes the TOTAL row the width-determining cell for any column.
- **Alignment/header-label exactness** (`format.py:92,98`) — `.rjust`→`.ljust` and header-label swaps survive because the alignment test only checks "no trailing whitespace," not per-column position.
- **Dead code:** unused local `periods = aggregated.periods` in `format_table` (`format.py:84`) — not a test gap, just dead code to delete.
- **Equivalent mutant:** `_period_sort_key` removal (`aggregate.py:54`).

**Takeaway:** `pipeline.py` (orchestration) is airtight. The remaining gaps are concentrated in exact-string/exact-position assertions and a couple of genuinely dead/unreachable branches — the underlying logic is thoroughly covered. This is also the codebase whose independent, spec-faithful validation stage (re-parsing the rendered table rather than checking data against itself) was already flagged as its standout strength in the LLM-judged comparison — but note its headline weakness (spurious `ValidationError` on fractional HEADCOUNT) isn't itself a mutation-testing finding; mutmut can't reveal "the check is too strict," only "the check is under-tested."

---

## Rank 3 — `sol-2026-07-08_13-28-18/` (NT2, no TDD) — 84.2%

*Carried over from `tdd-analysis-01`'s analysis of this same codebase; re-verified here with an identical `mutmut run` (386/325/61, exact match).*

**By file:**

| File | Mutants | Killed | Survived | Score |
|---|---|---|---|---|
| `pipeline.py` | 11 | 11 | 0 | 100% |
| `aggregate.py` | 55 | 51 | 4 | 92.7% |
| `parse.py` | 70 | 60 | 10 | 85.7% |
| `validate.py` | 107 | 89 | 18 | 83.2% |
| `format.py` | 143 | 114 | 29 | 79.7% |

`format.py` is this project's weakest file both in absolute survivor count (29) and score — the largest single weak spot across all four codebases in the batch.

**Gaps:**
- **Error-payload fields checked inconsistently** (`parse.py:46-75`, `validate.py:30-42`) — `.raw` asserted on only 2 of 8 parse-error branches; `validate_output`'s empty-table/no-TOTAL-column checks never inspect `.reason` content at all.
- **`.get(key, default)` fallbacks in `aggregate.py:61,68` and `format.py:50,60,109,111`** — every test grid is fully populated, so the missing-key fallback path is never taken.
- **Label-column alignment** (`format.py:127-134`) — `ljust`/`rjust` swap on column 0 survives because all label strings in test fixtures happen to fit exactly.
- **`all_headcount` flag mutations** (`format.py:39`) — survive because no test uses a *mixed* category set (REVENUE + HEADCOUNT together) to prove the flag is correctly `False` in that case.
- **Zero-boundary values** — same pattern as rank 2, in `parse.py:65`, `format.py:24`, `validate.py:81,95`.
- **Equivalent mutant:** period sort key (`aggregate.py:33-52`).
- **Residual cosmetic literals** (~10 survivors) — `""`/`"TOTAL"` placeholder swaps in header construction, only partially checked elsewhere.

**Takeaway:** Similar profile to rank 2 but the gaps are wider — particularly the `.get()` fallback and alignment clusters in `format.py` — consistent with a somewhat less exhaustive test suite for the formatting layer specifically. This project's already-known headline weakness (crashing on `NaN`/`Infinity` instead of raising a `ParseError`) is a genuine correctness bug, but again isn't something mutmut would surface directly — no mutation of *existing* code reproduces "the code fails to validate a case it should."

---

## Rank 4 — `sol-2026-07-10_11-23-40/` (T2, TDD) — 81.1%

Single-file codebase: all of `parse`/`aggregate`/`validate_output`/`format_table`/`run_pipeline` live in `report_pipeline/pipeline.py`, with `tests/` as a sibling directory.

**By function:**

| Function | Mutants | Killed | Survived | Score |
|---|---|---|---|---|
| `run_pipeline` | 10 | 10 | 0 | 100% |
| `_valid_period` | 7 | 7 | 0 | 100% |
| `_period_sort_key` | 6 | 6 | 0 | 100% |
| `aggregate` | 66 | 58 | 8 | 87.9% |
| `format_table` | 111 | 92 | 19 | 82.9% |
| `parse` | 72 | 54 | 18 | 75.0% |
| `validate_output` | 46 | 31 | 15 | **67.4%** (weakest function in the whole batch) |

**Flagged — closest to real risk:**
- **Zero-value REVENUE/HEADCOUNT boundary untested** (`pipeline.py:87`, `x_parse__mutmut_52`, `value < 0` → `<= 0`) — same shape as T1's two instances above; no test exercises `value == 0` for either category.
- **Table alignment direction never structurally verified** (`pipeline.py:222`, `x_format_table__mutmut_87`, `cell.rjust(w)` → `cell.ljust(w)`) — a real, user-visible rendering defect (misaligned numeric columns) that the existing width-only test (`test_format_column_no_narrower_than_header`) cannot catch.
- **Structural, not just coverage: `validate_output`'s `.get(key, default)` fallback survivors expose why this codebase's already-known headline weakness (tautological validation) is real.** `validate_output` re-derives `expected_total`/`expected_grand` (lines 267-280) from the *same* `agg` fields it checks against, using the same summation logic as `aggregate()` itself. The `.get()`-fallback mutants surviving at `aggregate.py:132`/`format_table:178`/`validate_output:269` aren't just "add a sparse fixture" gaps — they're evidence that `validate_output` **structurally cannot** catch a bug inside `aggregate()`, only a mismatch manually fabricated in a hand-built test fixture. This is the mutation-testing-visible fingerprint of the already-identified design flaw, not a new bug, but it's a stronger, more concrete demonstration of it than the original LLM review gave.

**Gaps:**
- **Error-message text asserted only via substring/keyword** (largest cluster: `parse` `x_parse__mutmut_11/12/20/22/29/30/31/43/44/45`, `validate_output` `x_validate_output__mutmut_7/8/17/18/19/44/45/46`) — same shape as every other codebase.
- **`raw_input`/`reason` dead-arg swaps to `None`** (`x_parse__mutmut_16/25/26/39/54/60`, `x_validate_output__mutmut_16/43`) — a regression nulling out the echoed input on most (5 of 6) `ParseError` call sites would go unnoticed; only one call site's `raw_input` is actually asserted.
- **Cosmetic layout under-asserted by "contains" checks** (`x_format_table__mutmut_77` padding-width, `x_format_table__mutmut_59/64/65/96` `"TOTAL"` label mutations) — `test_format_two_spaces_padding_between_columns` asserts `"  " in line` (at-least-2, not exactly-2), so 3-space padding still passes.
- **Equivalent mutants:** `sum(iterable, Decimal(0))` → `sum(iterable, )` dropped explicit start (`x_aggregate__mutmut_26/39/52`, `x_validate_output__mutmut_24/39`) — verified experimentally that `Decimal` vs implicit-`int`-then-`Decimal` behave identically for every value in this domain; and period-sort-key removal (`x_aggregate__mutmut_17/19`) — same cross-cutting pattern #5.

**Takeaway:** `run_pipeline`, `_valid_period`, and `_period_sort_key` are fully covered — the integration-level and period-parsing logic are solid. The weakness is concentrated in `validate_output` (67.4%, worst function in the batch) and `parse` (75.0%), and the `validate_output` gaps in particular aren't cosmetic — they're the mutation-testing evidence for this codebase's already-flagged tautological-validation design flaw.

---

## Overall observations

- **No codebase has a mutation survivor that reveals a currently-wrong behavior** — every survivor is either (a) a message/formatting-text exactness gap, (b) an untested boundary (zero, exact tolerance) that's currently handled correctly but unguarded against regression, (c) a defensive/fallback branch that's dead code under the test suite's data shapes, or (d) an equivalent mutant (period-sort key, `sum()`'s explicit start argument). The **recurring zero-boundary gap** (present in all four, and doubly so in T1) is the one pattern worth prioritizing as a fix, since it's plausible, realistic input that nobody tries.
- **The mutation-score ranking agrees exactly with the LLM-judged quality ranking** (T1 > NT1 > NT2 > T2) already established in this batch's `README.md`/`COMPARISON-REPORT.md` — a genuinely independent metric (mechanical mutation coverage, not an LLM's read of design/code/tests) landing on the same order. This is a different outcome from `tdd-analysis-01`, where both non-TDD runs beat both TDD runs on both metrics; here, the TDD run built with the expanded/refined TDD prompt (T1) tops the batch on both axes, while the other TDD run (T2, same prompt, much shorter/cheaper session) still comes in last. Read together, this suggests the earlier TDD-prompt weaknesses were addressable, but the *how thoroughly the session was actually driven* still matters more than the TDD/non-TDD label itself — sample size is still only 2-vs-2, so treat this as a suggestive data point, not a proof, consistent with [`TDD-PROMPT-ANALYSIS.md`](TDD-PROMPT-ANALYSIS.md)'s existing discussion.
- **Mutation testing surfaces the *mechanism* behind two of the four already-known headline weaknesses, adding concrete evidence rather than new bugs**: T1's `format_value` sentinel-category-string branch (Cluster B in the per-codebase section above) is the same fragile mechanism behind its known "HEADCOUNT-only TOTAL row printed as `$`" bug; T2's `.get()`-fallback survivors in `validate_output` are the mutation-testing fingerprint of its known "tautological validation" flaw — showing structurally, not just anecdotally, that it can never catch a bug `aggregate()` itself introduces. Neither NT1's fractional-HEADCOUNT-rejection bug nor NT2's NaN/Infinity crash has a corresponding mutation survivor, because both are bugs of *missing* validation (code that doesn't exist can't be mutated) rather than *under-tested existing* code — a reminder that mutation testing measures test thoroughness against the code as written, not spec conformance.
- **The same fix recipe would raise every project's score substantially**: (1) assert exact error-message text and full field sets instead of substring/`isinstance` checks, (2) add one zero-value test per numeric boundary check (this is the one with the best risk/effort ratio, appearing in every codebase), (3) add one sparse/partial-grid fixture per project to exercise `.get()` fallbacks, (4) add one exact full-line string assertion (not "contains") to pin down table layout and alignment direction.
