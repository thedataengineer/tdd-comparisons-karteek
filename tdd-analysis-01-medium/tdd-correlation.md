# Does TDD Explain the Test-Quality Gap?

A follow-up to `comparison-report.md`. After ranking the four solutions on test
quality, a pattern emerged: the two lowest-ranked solutions were the ones built
under **strict test-first (TDD) instructions**, and the two highest-ranked were
not. This document traces the original agent session transcripts to see whether
the TDD *approach* mechanistically explains the weaker tests.

## The correlation

| Rank | Solution | Scenario | TDD? | Tests | Notable test defect |
|------|----------|----------|------|-------|---------------------|
| 🥇 1 | `sol-…13-28-18` | `tdd-medium-no` | No | 75 | one dead test (no assert) |
| 🥈 2 | `sol-…12-57-29` | `tdd-medium-no` | No | 107 | coverage padded w/ monkeypatch tests |
| 🥉 3 | `sol-…13-18-28` | `tdd-medium` | **Yes** | 30 | circular/tautological validation |
| 4 | `sol-…13-41-45` | `tdd-medium` | **Yes** | 34 | a test **enshrines a bug** |

(`tdd-medium-no` = the "no" suffix means *no* strict-TDD instruction. The task
spec itself was byte-identical across all four; only the trailing instruction
block differed.)

### What differed in the instructions

Both arms were told to "aim for at least 80% line and branch coverage." The TDD
arm additionally got a strict red-green-refactor mandate:

> Follow this loop for every piece of behavior… 1. Write ONE test… 2. Run it
> and confirm it fails (red)… 3. Write the minimum implementation needed to make
> that test pass… 4. Run the full suite (green)… Never write implementation code
> before there is a failing test that requires it. Never write more than one new
> test at a time. Do not edit or weaken an existing test to make it pass.

The non-TDD arm got only: "Write tests alongside your implementation and aim for
at least 80% coverage."

## The claim being tested

Not "TDD produces bad tests" flatly. Specifically: the TDD runs produced **fewer
tests** (30, 34 vs 75, 107) and **hollower tests**, and the hollowness landed
exactly on the stages that decided the ranking (output validation; the TOTAL
row). The TDD runs' **parse-stage tests were genuinely good** — that is where
red-green shines.

## The key surprise

Reading the transcripts, **TDD discipline was followed faithfully in both TDD
runs** — red-before-green on every new symbol, one test at a time, no test ever
weakened. So the weak outcome is not a discipline failure. It is a structural
consequence of the loop as specified. Three mechanisms.

### Mechanism 1 — "minimum code to pass" manufactures circular tests (3rd place)

The happy-path validation test fed `format_table(agg)`'s own output straight
into `validate_output(table, agg)`. The cheapest code that passes "a valid table
validates OK" is to re-run the formatter and compare:

```python
expected = format_table(aggregated)
if table != expected:
    return {"error": "validation_error", "reason": "table content does not match aggregated data"}
return table
```

This is circular — it never independently checks TOTAL columns against row sums
(the spec's actual stage-4 requirement). The follow-up "mismatch" tests only fed
*hand-tampered strings*, which the tautology also rejects, so nothing ever forced
a real arithmetic check. In its own reasoning the agent noted the check was
"mostly a sanity check" and moved on because the test was green. **The test
locked in the hollow implementation.** The "column narrower than header" check
degenerated the same way — no test ever supplied a too-narrow column, so
minimum-code produced a substring-presence check instead of a width comparison.

### Mechanism 2 — "test-first, don't revisit green" enshrines unexamined decisions (4th place)

The pivotal moment was a single line of reasoning — *"Next - period subtotals:"*
— followed immediately by a test asserting the buggy value:

```python
# subtotal = sum of all category values in the period
assert result["period_subtotals"]["2024-Q1"] == pytest.approx(810.0)  # 1000 - 200 + 10
```

`810.0` folds a **headcount (10 people)** into a **dollar** subtotal. No
deliberation about whether mixing units is correct — the spec formats HEADCOUNT
as a plain integer and REVENUE/COST with `$`, a strong signal they are different
units, but the "next small behavior → make it green → don't touch passing tests"
cadence converted an unexamined choice into a hard, asserted contract. Later the
agent literally rendered `TOTAL $805.00` and did not react. Any fix now breaks a
passing test — which the rules explicitly discourage. TDD turned a design smell
into a locked-in regression the suite actively defends.

### Mechanism 3 — coverage-as-finish-line + one-test-at-a-time stops early and tests backwards

Both arms had the 80% coverage target, but strict TDD amplified it two ways:

- A **thin** implementation reaches ~100% coverage fast (a tautological
  validator has almost no branches), so the loop hit its stopping rule at ~30
  tests and declared done.
- The last third of both TDD sessions was spent reading `--cov-report`
  missing-line numbers and **reverse-engineering tests to color them green** —
  producing `isinstance(result, str)`-only "coverage-padding" tests for
  defensive `except` branches, while the real spec requirement (Check #3) got a
  test that *never went red* and a stub implementation. (Per the rules, a test
  that passes on arrival "isn't testing anything new — revise it"; the agent
  skipped that signal.)

The deepest point: under "never write code without a failing test," **any
behavior the agent didn't spontaneously think to test got neither a test nor
code** — which is why duplicate-ROW_ID and nan/inf handling silently fell out of
scope in both TDD runs.

By contrast, the non-TDD runs designed the whole system first, saw the full
surface area, then tested across it (75, 107 tests). No coverage gate
short-circuited them and no one-behavior-at-a-time cadence bounded the suite to
spontaneously-enumerated cases.

## Honest caveats

- **Tiny sample.** 2 vs 2. Suggestive, not conclusive; more runs per arm are
  needed to trust the direction.
- **Confound.** The two TDD runs happened to be the dict/`float`-based solutions
  and the two non-TDD ones the dataclass/`Decimal` solutions, so some of the
  quality gap is a data-modeling choice, not the process. But the
  *test-specific* failures (circular validation, enshrined bug, coverage
  padding) trace directly to the TDD loop in the transcripts, independent of the
  data-type choice.
- **TDD genuinely helped the parse stage** in both runs — discrete, enumerable
  error rules are the ideal fit for red-green. It hurt precisely where "correct"
  is a judgment call (validation semantics, the TOTAL row) rather than an
  enumerable rule.

## Bottom line

The mechanism is not "TDD writes bad tests." It is that **strict test-first +
minimum-code-to-pass + coverage-as-done** rewards tests that are cheap to satisfy
and stops when a *metric*, not the *spec*, is met. That combination (a) lets
hollow implementations be locked in by the very tests meant to specify them, (b)
enshrines unexamined design decisions as contracts the suite then defends, and
(c) terminates early with a suite reverse-engineered from coverage gaps. In this
task, those dynamics produced the two weakest test suites — even though the TDD
discipline itself was followed correctly.
