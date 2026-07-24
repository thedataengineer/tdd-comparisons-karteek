# Evaluation Results Summary

Summary of the latest JSON result files for `tdd-small` and `tdd-small-no` scenarios.

## Results files

| ID | TDD used? | Full session | Solution summary | Scenario | Codebase | TDD judgment |
|----|-----------|-----------|--------|----------|----------|----------------|
| T1 | Yes | [tdd-small_2026-07-09_09-42-14.json](tdd-small_2026-07-09_09-42-14.json) | [solution-summary-1783590349381.md](sol-2026-07-09_11-42-10/solution-summary-1783590349381.md) | tdd-small | [sol-2026-07-09_11-42-10](sol-2026-07-09_11-42-10/) | [did-it-do-tdd.md](sol-2026-07-09_11-42-10/did-it-do-tdd.md) |
| T2 | Yes | [tdd-small_2026-07-09_08-47-41.json](tdd-small_2026-07-09_08-47-41.json) | [tdd-analysis-1783587098546.md](sol-2026-07-09_10-47-37/tdd-analysis-1783587098546.md) | tdd-small | [sol-2026-07-09_10-47-37](sol-2026-07-09_10-47-37/) | [did-it-do-tdd.md](sol-2026-07-09_10-47-37/did-it-do-tdd.md) |
| NT1 | No | [tdd-small-no_2026-07-09_09-55-46.json](tdd-small-no_2026-07-09_09-55-46.json) | [tdd-analysis-1783591048584.md](sol-2026-07-09_11-55-41/tdd-analysis-1783591048584.md) | tdd-small-no | [sol-2026-07-09_11-55-41](sol-2026-07-09_11-55-41/) | — |
| NT2 | No | [tdd-small-no_2026-07-09_10-00-00.json](tdd-small-no_2026-07-09_10-00-00.json) | [eval-report-1783591302009.md](sol-2026-07-09_11-59-54/eval-report-1783591302009.md) | tdd-small-no | [sol-2026-07-09_11-59-54](sol-2026-07-09_11-59-54/) | — |

## Run Stats

(Turns = Number of times the model acted, counted by number of assistant messages)

| ID | TDD used? | JSON File | Tool Calls | Turns | Messages | Output Tokens | Input Tokens | Cache Read | Cache Write | Total Tokens | Duration (s) |
|----|----------|-----------|-----------|-------|----------|---------------|--------------|------------|-------------|--------------|--------------|
| T1 | Yes | tdd-small_2026-07-09_09-42-14.json | 37 | 55 | 111 | 12,821 | 57 | 852,267 | 29,306 | 894,451 | 215.0 |
| T2 | Yes | tdd-small_2026-07-09_08-47-41.json | 26 | 68 | 136 | 14,638 | 70 | 1,099,865 | 27,466 | 1,142,039 | 236.9 |
| NT1 | No | tdd-small-no_2026-07-09_09-55-46.json | 15 | 10 | 20 | 7,468 | 14 | 97,487 | 17,139 | 122,108 | 101.9 |
| NT2 | No | tdd-small-no_2026-07-09_10-00-00.json | 20 | 10 | 20 | 7,317 | 12 | 99,260 | 10,933 | 117,522 | 100.9 |


- **TDD runs** (tdd-small): More tool calls (26-37), more turns (55-68), longer duration (215-237s), and significantly more total tokens (890K-1.1M)
- **Non-TDD runs** (tdd-small-no): Fewer tool calls (15-20), fewer turns (10), shorter duration (~101s), and fewer total tokens (117K-122K)
- The TDD runs used significantly more cache, with cache read tokens accounting for ~95% of total tokens


## Overall judging by Opus

| Rank | TDD? | ID | Solution | Design | Code | Tests | Verdict |
|------|----- |----|----------|:------:|:----:|:-----:|---------|
| 🥇 1 | No | NT1 | **`sol-2026-07-09_11-55-41`** | 8 | 9 | 9 | Best overall — dataclass result, no bugs, 61 reason-asserting tests |
| 🥈 2 | No | NT2 | **`sol-2026-07-09_11-59-54`** | 8 | 8 | 8 | Very close — dataclass result, but a Unicode-digit spec deviation |
| 🥉 3 | Yes | T1 | **`sol-2026-07-09_11-42-10`** | 7 | 8 | 7 | Correct & clean, but dict result + fewer tests + dead code |
| 4 | Yes | T2 | **`sol-2026-07-09_10-47-37`** | 6 | 7 | 7 | Weakest design (free-text error) + a genuine crash bug |


## Mutation Testing Results

Ran `mutmut` against each codebase's `slot_validator` package, isolated in a per-project `.venv`. Ranked by mutation score. Full gap analysis: [`mutation_testing.md`](mutation_testing.md).

| Rank | TDD used? | ID | Codebase | Total Mutants | Killed | Survived | Mutation Score |
|---|---|---|---|---|---|---|---|
| 1 | Yes | T1 | `sol-2026-07-09_11-42-10/` | 110 | 103 | 7 | 93.6% |
| 2 | Yes | T2 | `sol-2026-07-09_10-47-37/` | 117 | 109 | 8 | 93.2% |
| 3 | No | NT2 | `sol-2026-07-09_11-59-54/` | 209 | 193 | 16 | 92.3% |
| 4 | No | NT1 | `sol-2026-07-09_11-55-41/` | 173 | 155 | 18 | 89.6% |

## Comparison approach
- Task that was used: [`task.md`](task.md)
- I made sure there were no  mentions of TDD to try and hide from the comparison that it was created in different workflows, to let it focus purely on the results
- Prompt to compare the results: [`compare.md`](compare.md); Used Opus, asked to send off subagents for each first

## Comparison results
- Comparison results: [`comparison-report.md`](comparison-report.md)
- Results interestingly ranked the two non-TDD runs first. Gave Opus access to the original conversations, and asked it to analyse if there is any correlation to the TDD approach, results: [`workflow-quality-correlation.md`](workflow-quality-correlation.md)

NB: Comparison discussion overall with Opus cost ~$5

## Summary

| Rank | ID | TDD | Design | Code | Tests | Avg | Test Count | Coverage | Mutation Score | Total Tokens | Turns | Tool Calls | Verdict |
|------|----|-----|--------|------|-------|-----|------------|----------|----------------|--------------|-------|------------|---------|
| 🥇 1 | NT1 | No | 8 | 9 | 9 | 8.67 | 61 | 100% | 89.6% | 122,108 | 10 | 15 | Best overall — dataclass result, no bugs, 61 reason-asserting tests |
| 🥈 2 | NT2 | No | 8 | 8 | 8 | 8.0 | 58 | 100% | 92.3% | 117,522 | 10 | 20 | Very close — dataclass result, but a Unicode-digit spec deviation |
| 🥉 3 | T1 | Yes | 7 | 8 | 7 | 7.33 | 21 | 100% | 93.6% | 894,451 | 55 | 37 | Correct & clean, but dict result + fewer tests + dead code |
| 4 | T2 | Yes | 6 | 7 | 7 | 6.67 | 20 | 100% | 93.2% | 1,142,039 | 68 | 26 | Weakest design (free-text error) + a genuine crash bug |