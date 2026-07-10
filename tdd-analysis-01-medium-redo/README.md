
I realised a bit late that in `tdd-analysis-01-medium`, the TDD adherance by the TDD tasks was a bit flimsier than I thought, so I reran those. Also added two solutions created with the instructions to write tests first (but no further instructions about a full-blown TDD workflow, with red tests first, etc). This comparison reuses the same non-TDD solutions generated in `tdd-analysis-01-medium`

# Evaluation Results Summary

Summary of the latest JSON result files for the `tdd-medium`, `tdd-medium-no`,
and `test-first-medium` scenarios — the same task (`task.md`: a 4-stage report
pipeline), run twice under each of three development-process instructions:

- **`tdd-medium-no`** — no process instruction; tests may be written any time (IDs `NT1`, `NT2`)
- **`tdd-medium`** — strict TDD instructed (red → green, one test at a time) (IDs `T1`, `T2`)
- **`test-first-medium`** — tests must be written before implementation, but not strict red/green TDD (IDs `TF1`, `TF2`)

## Results files

| ID | Approach | Full session | Solution report | Scenario | Codebase |
|----|----------|--------------|------------------|----------|----------|
| NT1 | No TDD | [tdd-medium-no_2026-07-08_11-57-32.json](tdd-medium-no_2026-07-08_11-57-32.json) | [analysis-1783512340492.md](sol-2026-07-08_12-57-29/analysis-1783512340492.md) | tdd-medium-no | [sol-2026-07-08_12-57-29](sol-2026-07-08_12-57-29/) |
| NT2 | No TDD | [tdd-medium-no_2026-07-08_12-28-23.json](tdd-medium-no_2026-07-08_12-28-23.json) | [solution-summary-1783514194167.md](sol-2026-07-08_13-28-18/solution-summary-1783514194167.md) | tdd-medium-no | [sol-2026-07-08_13-28-18](sol-2026-07-08_13-28-18/) |
| T1 | TDD | [tdd-medium_2026-07-10_14-40-55.json](tdd-medium_2026-07-10_14-40-55.json) | [tdd-analysis-1783694844961.md](sol-2026-07-10_16-40-51/tdd-analysis-1783694844961.md) | tdd-medium | [sol-2026-07-10_16-40-51](sol-2026-07-10_16-40-51/) |
| T2 | TDD | [tdd-medium_2026-07-10_14-51-21.json](tdd-medium_2026-07-10_14-51-21.json) | [tdd-analysis-1783695499889.md](sol-2026-07-10_16-51-18/tdd-analysis-1783695499889.md) | tdd-medium | [sol-2026-07-10_16-51-18](sol-2026-07-10_16-51-18/) |
| TF1 | Test-first | [test-first-medium_2026-07-10_15-04-52.json](test-first-medium_2026-07-10_15-04-52.json) | [eval-supplementary-1783696101803.md](sol-2026-07-10_17-04-49/eval-supplementary-1783696101803.md) | test-first-medium | [sol-2026-07-10_17-04-49](sol-2026-07-10_17-04-49/) |
| TF2 | Test-first | [test-first-medium_2026-07-10_15-14-16.json](test-first-medium_2026-07-10_15-14-16.json) | [eval-supplementary-1783696743736.md](sol-2026-07-10_17-11-55/eval-supplementary-1783696743736.md) | test-first-medium | [sol-2026-07-10_17-11-55](sol-2026-07-10_17-11-55/) |

## When were tests written?

The judge model (running as the evaluator) inspected each session's tool-call
sequence for evidence of when tests were written relative to implementation.

| ID | Verdict |
|----|---------|
| NT1 | Tests written **after** implementation (all 5 source files, then all 5 test files) — expected for this variant. |
| NT2 | Batch impl-then-test (all sources ~12:28–12:29, then all tests ~12:29–12:31) — appropriate for "without TDD". |
| T1 | **Yes, very strictly** — clear red→green loop for each of 25 tests; one new test at a time, run-to-fail confirmed, minimal implementation, full suite re-run each time. |
| T2 | **Yes, strongly** — same write-test → run-fails → implement → run-passes loop for all 29 tests across all four stages; no existing test weakened. |
| TF1 | **Test-first**, all tests written before implementation, but not strict red-green-refactor (no incremental fail-then-pass loop). |
| TF2 | **Test-first**, all tests written upfront in one batch, then implementation, with no intermediate test run in between — satisfies "tests before implementation" but not incremental TDD. |

## Run Stats

(Turns = number of times the model acted, counted by number of assistant messages)

| ID | Approach | JSON File | Tool Calls | Turns | Messages | Output Tokens | Input Tokens | Cache Read | Cache Write | Total Tokens | Duration (s) |
|----|----------|-----------|-----------|-------|----------|---------------|--------------|------------|-------------|--------------|--------------|
| NT1 | No TDD | tdd-medium-no_2026-07-08_11-57-32.json | 20 | 21 | 42 | 33,644 | 23 | 623,328 | 46,164 | 703,159 | 488.0 |
| NT2 | No TDD | tdd-medium-no_2026-07-08_12-28-23.json | 30 | 31 | 62 | 32,220 | 33 | 699,161 | 38,400 | 769,814 | 491.0 |
| T1 | TDD | tdd-medium_2026-07-10_14-40-55.json | 89 | 90 | 180 | 22,992 | 92 | 1,954,580 | 40,075 | 2,017,739 | 389.8 |
| T2 | TDD | tdd-medium_2026-07-10_14-51-21.json | 95 | 96 | 192 | 23,234 | 98 | 2,041,906 | 34,042 | 2,099,280 | 418.2 |
| TF1 | Test-first | test-first-medium_2026-07-10_15-04-52.json | 16 | 17 | 34 | 13,535 | 18 | 236,557 | 18,213 | 268,323 | 209.4 |
| TF2 | Test-first | test-first-medium_2026-07-10_15-14-16.json | 26 | 27 | 54 | 20,176 | 28 | 568,827 | 30,500 | 619,531 | 286.7 |

- **TDD runs** (T1, T2) used by far the most tool calls (89–95) and turns (90–96), and the most total tokens (2.0–2.1M) — one tool call per red/green cycle adds up fast for a 4-stage pipeline.
- **No-TDD runs** (NT1, NT2) sit in the middle: fewer tool calls (20–30) than TDD but noticeably more than test-first, with the longest wall-clock duration (488–491s) despite far fewer turns than TDD — likely from a couple of large batched edits plus iterative coverage fix-up passes.
- **Test-first runs** (TF1, TF2) were the cheapest and fastest by a wide margin (16–26 tool calls, 209–287s, 268K–620K total tokens) — writing all tests in one batch upfront, without a per-test red/green loop, avoids most of the tool-call overhead TDD incurs.
- Across all runs, cache-read tokens dominate total token usage (~85–95%), consistent with the pattern seen in the earlier `tdd-small` comparison — the effect scales with the number of turns, since each turn re-reads the growing conversation history.

## Quality ranking

A separate pass (see [comparison_report.md](comparison_report.md)) had six
independent reviewer subagents assess each solution's design, code quality,
and test effectiveness, then ran every test suite. Cross-referencing that
ranking with the IDs above:

| Rank | ID | Solution | Design | Code | Tests | Overall | Test result | Impl / Test LOC |
|------|----|----------|:------:|:----:|:-----:|:-------:|-------------|-----------------|
| 🥇 1 | **NT1** | sol-2026-07-08_12-57-29 | 8 | 8 | 8 | **8.0** | 107 passed | 497 / 881 |
| 🥈 2 | **TF2** | sol-2026-07-10_17-11-55 | 8 | 8 | 7 | **8.0** | 90 passed | 484 / 850 |
| 🥉 3 | **NT2** | sol-2026-07-08_13-28-18 | 8 | 8 | 7 | **7.5** | 75 passed | 330 / 430 |
| 4 | **T2** | sol-2026-07-10_16-51-18 | 7 | 7 | 6 | **6.5** | 29 passed | 207 / 304 |
| 5 | **TF1** | sol-2026-07-10_17-04-49 | 6 | 6 | 6 | **6.0** | 62 passed | 348 / 360 |
| 6 | **T1** | sol-2026-07-10_16-40-51 | 6 | 6 | 6 | **6.0** | 25 passed | 142 / 228 |

- The two **No-TDD** runs took the top and 3rd spots, both multi-module solutions with the deepest test suites (75–107 tests) and the most defensive parse-stage validation.
- The two **TDD** runs landed 4th and last — smallest implementations (142–207 LOC), fewest tests (25–29), and both graded 6–6.5 overall. Rigorous red/green discipline didn't translate into more thorough coverage of edge cases here; each cycle covered only the one behavior needed to pass the next test, so nothing beyond the tests the agent thought to write ever got exercised.
- The two **test-first** runs split — TF2 tied for 2nd (largest test-first suite, 90 tests, `Decimal` throughout) while TF1 landed 5th (had the strongest parser of the three single-file solutions, but shipped visible dead scaffolding and a broken TOTAL row).
- This is a small sample (2 runs per condition), so treat the TDD-loses-on-quality result as suggestive rather than conclusive — but it's a clear reversal of the intuition that stricter test discipline yields more robust code.
- Note: the per-session scores in the [Results files](#results-files) reports (0.75–0.92) are **process-adherence** checks — each verifies against its own per-scenario rubric that the assigned process was actually followed (strict TDD really looped red→green, test-first really wrote tests first). They are not a quality or completion metric and are not comparable across conditions; their only role here is to confirm this is a genuine process difference, not just a prompting difference. See [process_quality_correlation.md](process_quality_correlation.md) for the process→quality analysis.


## Comparison approach
- Task that was used: [`task.md`](task.md)
- Same six-solution set as the ranking above (2× no-TDD, 2× strict TDD, 2× test-first), with no mentions of process in the solutions themselves so it could be judged on results alone
- Prompted Opus to compare the results: [`compare.md`](compare.md); used six independent reviewer subagents (design, code quality, test effectiveness) plus a full test-suite run per solution

## Comparison results
- Comparison results: [`comparison_report.md`](comparison_report.md)
- Process → quality correlation analysis, cross-referencing the blind quality ranking against each session's actual process (mined only after ranking, to avoid bias): [`process_quality_correlation.md`](process_quality_correlation.md)
- As in the original `tdd-analysis-01-medium` comparison, the no-TDD runs ranked highest; here test-first split across the ranking while strict TDD again landed at the bottom, reinforcing the earlier result now that TDD adherence itself was verified more rigorously
