# Evaluation Results Summary

Summary of the latest JSON result files for `tdd-medium-v2` and `tdd-medium-no` scenarios.

## Results files

| ID | TDD used? | Full session | Solution summary | Scenario | Codebase | TDD judgment |
|----|-----------|-----------|--------|----------|----------|----------------|
| T1 | Yes | [tdd-medium-v2_2026-07-10_08-17-47.json](tdd-medium-v2_2026-07-10_08-17-47.json) | [analysis-1783673009287.md](sol-2026-07-10_10-17-42/analysis-1783673009287.md) | tdd-medium-v2 | [sol-2026-07-10_10-17-42](sol-2026-07-10_10-17-42/) | [did-it-do-tdd.md](sol-2026-07-10_10-17-42/did-it-do-tdd.md) |
| T2 | Yes | [tdd-medium-v2_2026-07-10_09-23-44.json](tdd-medium-v2_2026-07-10_09-23-44.json) | [medium-v2_2026-07-10_09-23-44-supplementary.md](sol-2026-07-10_11-23-40/medium-v2_2026-07-10_09-23-44-supplementary.md) | tdd-medium-v2 | [sol-2026-07-10_11-23-40](sol-2026-07-10_11-23-40/) | [did-it-do-tdd.md](sol-2026-07-10_11-23-40/did-it-do-tdd.md) |
| NT1 | No | [tdd-medium-no_2026-07-08_11-57-32.json](tdd-medium-no_2026-07-08_11-57-32.json) | [analysis-1783512340492.md](sol-2026-07-08_12-57-29/analysis-1783512340492.md) | tdd-medium-no | [sol-2026-07-08_12-57-29](sol-2026-07-08_12-57-29/) | — |
| NT2 | No | [tdd-medium-no_2026-07-08_12-28-23.json](tdd-medium-no_2026-07-08_12-28-23.json) | [solution-summary-1783514194167.md](sol-2026-07-08_13-28-18/solution-summary-1783514194167.md) | tdd-medium-no | [sol-2026-07-08_13-28-18](sol-2026-07-08_13-28-18/) | — |

**NT1 and NT2 are the same codebases as used in tdd-analysis-01-medium. T1 and T2 were freshly created with an expanded TDD instruction prompt, based on Opus's recommendations after analysing previous TDD sessions and why their design might have been deemed worse. It's in [`instructions.ts`](../instructions.ts) under `with_tdd_improved`**

## Run Stats

(Turns = number of assistant messages; Tool Calls = number of `toolCall` blocks across those messages)

| ID | TDD used? | JSON File | Tool Calls | Turns | Messages | Output Tokens | Input Tokens | Cache Read | Cache Write | Total Tokens | Duration (s) |
|----|----------|-----------|-----------|-------|----------|---------------|--------------|------------|-------------|--------------|--------------|
| T1 | Yes | tdd-medium-v2_2026-07-10_08-17-47.json | 116 | 117 | 234 | 34,461 | 118 | 3,305,797 | 106,907 | 3,447,283 | 1541.5 |
| T2 | Yes | tdd-medium-v2_2026-07-10_09-23-44.json | 60 | 61 | 122 | 20,079 | 62 | 1,365,594 | 35,936 | 1,421,671 | 336.7 |
| NT1 | No | tdd-medium-no_2026-07-08_11-57-32.json | 20 | 21 | 42 | 33,644 | 23 | 623,328 | 46,164 | 703,159 | 488.0 |
| NT2 | No | tdd-medium-no_2026-07-08_12-28-23.json | 30 | 31 | 62 | 32,220 | 33 | 699,161 | 38,400 | 769,814 | 491.0 |

- **TDD runs** (tdd-medium-v2): More tool calls (60-116), more turns (61-117), and dramatically more total tokens (1.42M-3.45M). Duration is noisier: T2 finished fastest of all four runs (336.7s) while T1 was by far the slowest (1541.5s).
- **Non-TDD runs** (tdd-medium-no): Fewer tool calls (20-30), fewer turns (21-31), consistent duration (~488-491s), and far fewer total tokens (703K-770K).
- As with the other scenarios, the TDD runs' token usage is dominated by cache reads (>95% of total).

## Quality Ranking

See [`COMPARISON-REPORT.md`](COMPARISON-REPORT.md) for full detail. Each solution was analysed
independently (source + tests read in full, tests executed, coverage measured, spec conformance
checked by running the code), then ranked on design appropriateness, code quality, and test
effectiveness.

| Rank | ID | TDD used? | Codebase | Design | Code | Tests | Tests run | Coverage | Headline weakness |
|------|----|-----------|----------|:------:|:----:|:-----:|:---------:|:--------:|-------------------|
| 🥇 1 | T1 | Yes | sol-2026-07-10_10-17-42 | 8 | 8 | 7 | 51 pass | 100% | HEADCOUNT-only TOTAL row printed as `$`; validation is a substring check, not arithmetic |
| 🥈 2 | NT1 | No | sol-2026-07-08_12-57-29 | 8 | 8 | 6 | 107 pass | 100% | Fractional HEADCOUNT → *spurious* ValidationError on valid input; tests lean on monkeypatching |
| 🥉 3 | NT2 | No | sol-2026-07-08_13-28-18 | 8 | 7 | 6 | 75 pass | 100% | `NaN`/`Infinity` crash the pipeline instead of a ParseError; validation re-runs the formatter |
| 4 | T2 | Yes | sol-2026-07-10_11-23-40 | 7 | 7 | 6 | 43 pass | 100% | Validation is **tautological** (checks aggregate against itself); width check is only a comment |

- All four pass their own suites at 100% line coverage, so **coverage is not a discriminator** —
  every solution still ships at least one real correctness bug.
- The **Validate stage** is what separates them: only NT1 independently re-parses the rendered
  table (most spec-faithful); T2's validator compares aggregate data against itself and can never
  fail on a real run.
- 1st vs 2nd is close: T1 has the cleanest architecture and best tests; NT1 has the only truly
  independent validation and the broadest suite, but rejects legitimate fractional-headcount input
  and manufactures part of its coverage via internal monkeypatching.

## Mutation Testing Results

Ran [`mutmut`](https://mutmut.readthedocs.io/) (v3.6.0) against each codebase's `report_pipeline` package, isolated in a per-project `.venv`. Ranked by mutation score (killed / total). Full gap analysis: [`mutation_testing.md`](mutation_testing.md).

| Rank | TDD | ID | Codebase | Total Mutants | Killed | Survived | Mutation Score |
|---|---|---|---|---|---|---|---|
| 1 | Yes | T1 | `sol-2026-07-10_10-17-42/` | 296 | 267 | 29 | 90.2% |
| 2 | No | NT1 | `sol-2026-07-08_12-57-29/` | 318 | 285 | 33 | 89.6% |
| 3 | No | NT2 | `sol-2026-07-08_13-28-18/` | 386 | 325 | 61 | 84.2% |
| 4 | Yes | T2 | `sol-2026-07-10_11-23-40/` | 318 | 258 | 60 | 81.1% |

This mutation-score ranking exactly matches the LLM-judged quality ranking above (T1 > NT1 > NT2 > T2) — a second, independent signal agreeing with the first. Note `sol-2026-07-08_12-57-29` and `sol-2026-07-08_13-28-18` are the same codebases analyzed in `tdd-analysis-01` (byte-identical source/tests, confirmed via diff); their mutation numbers reproduce exactly.

## Comparison approach
- Task that was used: [`task.md`](task.md)
- I made sure there were no  mentions of TDD to try and hide from the comparison that it was created in different workflows, to let it focus purely on the results
- Prompt to compare the results: [`compare.md`](compare.md); Used Opus, asked to send off subagents for each first

## Comparison results
- Comparison results: [`COMPARISON-REPORT.md`](COMPARISON-REPORT.md)
- Gave Opus access to the original conversations, pointed out that the TDD prompt in this run had been augmented with more focus on refactoring step and thinking about the overall contracts in the design first. Asked it to analyse the outcomes of T1 and T2 based on that background, results: [`TDD-PROMPT-ANALYSIS.md`](TDD-PROMPT-ANALYSIS.md)

## Summary

| Rank | ID | TDD | Design | Code | Tests | Avg | Test Count | Coverage | Mutation Score | Total Tokens | Turns | Tool Calls | Headline weakness |
|------|----|-----|--------|------|-------|-----|------------|----------|----------------|--------------|-------|------------|-------------------|
| 🥇 1 | T1 | Yes | 8 | 8 | 7 | 7.67 | 51 | 100% | 90.2% | 3,447,283 | 117 | 116 | HEADCOUNT-only TOTAL row printed as `$`; validation is a substring check, not arithmetic |
| 🥈 2 | NT1 | No | 8 | 8 | 6 | 7.33 | 107 | 100% | 89.6% | 703,159 | 21 | 20 | Fractional HEADCOUNT → spurious ValidationError on valid input; tests lean on monkeypatching |
| 🥉 3 | NT2 | No | 8 | 7 | 6 | 7.0 | 75 | 100% | 84.2% | 769,814 | 31 | 30 | `NaN`/`Infinity` crash the pipeline instead of a ParseError; validation re-runs the formatter |
| 4 | T2 | Yes | 7 | 7 | 6 | 6.67 | 43 | 100% | 81.1% | 1,421,671 | 61 | 60 | Validation is tautological (checks aggregate against itself); width check is only a comment |
