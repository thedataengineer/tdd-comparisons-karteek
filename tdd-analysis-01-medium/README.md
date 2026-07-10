## TDD Comparison Candidates

2 runs with TDD, 2 runs without; both were created with Sonnet-4.6

| ID | TDD | Full session | Solution summary | Codebase | TDD judgment |
|---|---|---|---|---|---|
| T1 | Yes | [`tdd-medium_2026-07-08_12-18-32.json`](tdd-medium_2026-07-08_12-18-32.json) | [`sol-2026-07-08_13-18-28/tdd-analysis-1783513418045.md`](sol-2026-07-08_13-18-28/tdd-analysis-1783513418045.md) | [`sol-2026-07-08_13-18-28/`](sol-2026-07-08_13-18-28/) | [`did-it-do-tdd.md`](sol-2026-07-08_13-18-28/did-it-do-tdd.md) |
| T2 | Yes | [`tdd-medium_2026-07-08_12-44-34.json`](tdd-medium_2026-07-08_12-44-34.json) | [`sol-2026-07-08_13-41-45/analysis-1783515149930.md`](sol-2026-07-08_13-41-45/analysis-1783515149930.md) | [`sol-2026-07-08_13-41-45/`](sol-2026-07-08_13-41-45/) | [`did-it-do-tdd.md`](sol-2026-07-08_13-41-45/did-it-do-tdd.md) |
| NT1 | No | [`tdd-medium-no_2026-07-08_12-28-23.json`](tdd-medium-no_2026-07-08_12-28-23.json) | [`sol-2026-07-08_13-28-18/solution-summary-1783514194167.md`](sol-2026-07-08_13-28-18/solution-summary-1783514194167.md) | [`sol-2026-07-08_13-28-18/`](sol-2026-07-08_13-28-18/) | — |
| NT2 | No | [`tdd-medium-no_2026-07-08_11-57-32.json`](tdd-medium-no_2026-07-08_11-57-32.json) | [`sol-2026-07-08_12-57-29/analysis-1783512340492.md`](sol-2026-07-08_12-57-29/analysis-1783512340492.md) | [`sol-2026-07-08_12-57-29/`](sol-2026-07-08_12-57-29/) | — |

## Run Stats

(Turns = Number of times the model acted, counted by number of assistant messages)

| ID | TDD | Conversation JSON | Tool Calls | Turns | Messages | Output Tokens | Total Tokens |
|---|---|---|---|---|---|---|---|
| T1 | Yes | `tdd-medium_2026-07-08_12-18-32.json` | 28 | 71 | 142 | 17,128 | 1,519,762 |
| T2 | Yes | `tdd-medium_2026-07-08_12-44-34.json` | 60 | 103 | 206 | 26,533 | 2,580,897 |
| NT1 | No | `tdd-medium-no_2026-07-08_12-28-23.json` | 37 | 31 | 62 | 32,220 | 769,814 |
| NT2 | No | `tdd-medium-no_2026-07-08_11-57-32.json` | 24 | 21 | 42 | 33,644 | 703,159 |

## Overall judging by Opus

| # | Solution | ID | Structure | Data types | Money | Tests | Result | Coverage |
|---|----------|----|-----------|-----------|-------|-------|--------|----------|
| 🥇 | `sol-…13-28-18` | NT1 | module-per-stage | dataclasses | `Decimal` | 75 | 75 pass | 100% |
| 🥈 | `sol-…12-57-29` | NT2 | module-per-stage | dataclasses | float/round | 107 | 107 pass | 100% |
| 🥉 | `sol-…13-18-28` | T1 | single module (TDD) | dicts | float | 30 | 30 pass | 100% |
| 4 | `sol-…13-41-45` | T2 | single module | dicts | float | 34 | 34 pass | 99% |

## Mutation Testing Results

Ran [`mutmut`](https://mutmut.readthedocs.io/) (v3.6.0) against each codebase's `report_pipeline` package, isolated in a per-project `.venv`. Ranked by mutation score (killed / total). Full gap analysis (done with Sonnet): [`mutation_testing.md`](mutation_testing.md).

| Rank | TDD | ID | Codebase | Total Mutants | Killed | Survived | Mutation Score |
|---|---|---|---|---|---|---|---|
| 1 | No | NT2 | `sol-2026-07-08_12-57-29/` | 318 | 285 | 33 | 89.6% |
| 2 | No | NT1 | `sol-2026-07-08_13-28-18/` | 386 | 325 | 61 | 84.2% |
| 3 | Yes | T1 | `sol-2026-07-08_13-18-28/` | 342 | 277 | 65 | 81.0% |
| 4 | Yes | T2 | `sol-2026-07-08_13-41-45/` | 361 | 279 | 82 | 77.3% |

## Comparison approach
- Task that was used: [`task.md`](task.md)
- I made sure there were no  mentions of TDD to try and hide from the comparison that it was created in different workflows, to let it focus purely on the results
- Prompt to compare the results: [`compare.md`](compare.md); Used Opus, asked to send off subagents for each first

## Comparison results
- Comparison results: [`comparison-report.md`](comparison-report.md)
- Results interestingly ranked the two non-TDD runs first. Gave Opus access to the original conversations, and asked it to analyse if there is any correlation to the TDD approach, results: [`tdd-correlation.md`](tdd-correlation.md)

NB: Comparison discussion overall with Opus cost ~$5