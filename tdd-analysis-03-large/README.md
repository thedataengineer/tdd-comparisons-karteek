# Evaluation Results Summary

Summary of the latest JSON result files for `tdd-large` and `tdd-large-no` scenarios.

## Results files

| ID | TDD used? | Full session | Solution summary | Scenario | Codebase | TDD judgment |
|----|-----------|-----------|--------|----------|----------|----------------|
| T1 | Yes | [tdd-large_2026-07-09_12-59-47.json](tdd-large_2026-07-09_12-59-47.json) | [eval-report-1783602274197.md](sol-2026-07-09_14-59-45/eval-report-1783602274197.md) | tdd-large | [sol-2026-07-09_14-59-45](sol-2026-07-09_14-59-45/) | [did-it-do-tdd.md](sol-2026-07-09_14-59-45/did-it-do-tdd.md) |
| T2 | Yes | [tdd-large_2026-07-09_13-12-58.json](tdd-large_2026-07-09_13-12-58.json) | [analysis-1783603068879.md](sol-2026-07-09_15-12-54/analysis-1783603068879.md) | tdd-large | [sol-2026-07-09_15-12-54](sol-2026-07-09_15-12-54/) | [did-it-do-tdd.md](sol-2026-07-09_15-12-54/did-it-do-tdd.md) |
| NT1 | No | [tdd-large-no_2026-07-09_13-23-35.json](tdd-large-no_2026-07-09_13-23-35.json) | [solution-summary-1783603613843.md](sol-2026-07-09_15-23-32/solution-summary-1783603613843.md) | tdd-large-no | [sol-2026-07-09_15-23-32](sol-2026-07-09_15-23-32/) | — |
| NT2 | No | [tdd-large-no_2026-07-09_13-44-44.json](tdd-large-no_2026-07-09_13-44-44.json) | [analysis-1783604937652.md](sol-2026-07-09_15-43-12/analysis-1783604937652.md) | tdd-large-no | [sol-2026-07-09_15-43-12](sol-2026-07-09_15-43-12/) | — |

Notes:
- JSON files live in `results/`; `codebasePath` in each JSON points at `tdd-2026-07-09_HH-MM-SS`, which was copied into this folder as `sol-2026-07-09_HH-MM-SS`.
- `evaluation.reports` in each JSON points at the report file under `results/`; that same file has been copied alongside its codebase here (T2/NT2 reports were renamed, dropping the `tdd-` prefix, to avoid revealing which run used TDD).

## Summary

| Rank | ID | TDD | Design | Code | Tests | Correctness | Avg | Test Count | Coverage | Mutation Score | Total Tokens | Turns | Tool Calls | Verdict |
|------|----|-----|--------|------|-------|-------------|-----|------------|----------|----------------|--------------|-------|------------|---------|
| 1 | NT2 | No | 8 | 9 | 8 | 8 | 8.25 | 69 | 100% | 86.9% | 322,148 | 14 | 13 | Only solution with real input validation; precise boundary tests; minor out-of-order purchase edge cases only |
| 2 | T2 | Yes | 7 | 7 | 8 | 8 | 7.5 | 22 | 99% | 85.6% | 1,225,517 | 63 | 62 | Clean typed data model, all core rules correct; no error handling, duplicate purchase ID bug, dead state fields |
| 3 | T1 | Yes | 7 | 7 | 7 | 9 | 7.5 | 21 | 99% | 85.2% | 1,253,300 | 67 | 66 | Most functionally correct (no bugs found on probing); untyped nested dicts, vestigial structure, fewest tests |
| 4 | NT1 | No | 8 | 7 | 6 | 6 | 6.75 | 74 | 99% | 89.4% | 185,094 | 11 | 9 | Highest design score, 74 tests — but two High bugs: wrong batch draw-down order; future-dated points counted as spendable |

## Run Stats

(Turns = number of assistant messages; Tool Calls = number of `toolCall` blocks across those messages)

| ID | TDD used? | JSON File | Tool Calls | Turns | Messages | Output Tokens | Input Tokens | Cache Read | Cache Write | Total Tokens | Duration (s) |
|----|----------|-----------|-----------|-------|----------|---------------|--------------|------------|-------------|--------------|--------------|
| T1 | Yes | tdd-large_2026-07-09_12-59-47.json | 66 | 67 | 134 | 15,925 | 69 | 1,207,631 | 29,675 | 1,253,300 | 286.3 |
| T2 | Yes | tdd-large_2026-07-09_13-12-58.json | 62 | 63 | 126 | 17,933 | 65 | 1,175,933 | 31,586 | 1,225,517 | 290.6 |
| NT1 | No | tdd-large-no_2026-07-09_13-23-35.json | 9 | 11 | 22 | 15,262 | 15 | 148,803 | 21,014 | 185,094 | 198.5 |
| NT2 | No | tdd-large-no_2026-07-09_13-44-44.json | 13 | 14 | 28 | 18,820 | 16 | 270,173 | 33,139 | 322,148 | 253.4 |

- **TDD runs** (tdd-large): Far more tool calls (62-66), more turns (63-67), longer duration (~286-291s), and dramatically more total tokens (~1.2M each)
- **Non-TDD runs** (tdd-large-no): Fewer tool calls (9-13), fewer turns (11-14), shorter duration (~199-253s), and far fewer total tokens (185K-322K)
- As with the "small" scenario, the TDD runs' token usage is dominated by cache reads (>95% of total)

## Quality Ranking

Ranking from [`comparison-report.md`](comparison-report.md), cross-referenced to
the run IDs above via the Codebase column. Labels A–D are the report's internal
labels; the **ID** column is the corresponding TDD / non-TDD run.

| Rank | ID | TDD used? | Label | Codebase | Design | Code | Tests | Correctness | Avg |
|------|----|-----------|-------|----------|--------|------|-------|-------------|-----|
| 1 | NT2 | No | D | sol-2026-07-09_15-43-12 | 8 | 9 | 8 | 8 | 8.25 |
| 2 | T2 | Yes | B | sol-2026-07-09_15-12-54 | 7 | 7 | 8 | 8 | 7.5 |
| 3 | T1 | Yes | A | sol-2026-07-09_14-59-45 | 7 | 7 | 7 | 9 | 7.5 |
| 4 | NT1 | No | C | sol-2026-07-09_15-23-32 | 8 | 7 | 6 | 6 | 6.75 |

- The two non-TDD runs bracket the field: **NT2 ranks 1st, NT1 ranks 4th** (the
  only solution with High-severity bugs).
- The two TDD runs land in the middle (**T2 2nd, T1 3rd**), tied on average (7.5).
- Test count did not track quality: NT1 has the most tests (74) but the worst
  correctness; T1 has the fewest (21) but the highest correctness.

## Mutation Testing Results

Ran `mutmut` against each codebase's package, isolated in a per-project `.venv`. Ranked by mutation score. Full gap analysis: [`mutation_testing.md`](mutation_testing.md).

| Rank | ID | TDD used? | Codebase | Total Mutants | Killed | Survived | Mutation Score |
|---|---|---|---|---|---|---|---|
| 1 | NT1 | No | `sol-2026-07-09_15-23-32/` | 132 | 118 | 14 | 89.4% |
| 2 | NT2 | No | `sol-2026-07-09_15-43-12/` | 130 | 113 | 17 | 86.9% |
| 3 | T2 | Yes | `sol-2026-07-09_15-12-54/` | 139 | 119 | 20 | 85.6% |
| 4 | T1 | Yes | `sol-2026-07-09_14-59-45/` | 203 | 173 | 30 | 85.2% |

- The two non-TDD runs bracket the top of the mutation-score ranking too (**NT1 1st, NT2 2nd**), but this *disagrees* with the human quality ranking above, where **NT1 ranked worst (4th)** due to High-severity correctness bugs and **NT2 ranked best (1st)**.
- This suggests NT1's tests are individually strict/precise (few survivors relative to mutants generated) but not comprehensive enough to cover the correctness bugs a human reviewer found — a reminder that mutation score measures how well existing tests exercise existing code, not whether the code (or the tests' assumptions) are correct.
- See [`mutation_testing.md`](mutation_testing.md) for the per-codebase breakdown of what the surviving mutants actually reveal.

## Task

## Comparison approach
- Task that was used: [`task.md`](task.md)
- I made sure there were no  mentions of TDD to try and hide from the comparison that it was created in different workflows, to let it focus purely on the results
- Prompt to compare the results: [`compare.md`](compare.md); Used Opus, asked to send off subagents for each first

## Comparison results
- Comparison results: [`comparison-report.md`](comparison-report.md)
- Gave Opus access to the original conversations, and asked it to hypothesise if there are any relationships between the TDD approach and its outcomes: [`workflow-trace-analysis.md`](workflow-trace-analysis.md)
