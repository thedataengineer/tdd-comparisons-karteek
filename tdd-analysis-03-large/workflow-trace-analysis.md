# Why Did the Non-TDD Workflow Produce the Best Solution?

## Trace analysis of the four coding-agent sessions

This report analyzes the full session traces (`*.json`) that produced the four
solutions, to form hypotheses for a counterintuitive result: **a non-TDD run
(NT2) ranked #1 in solution quality, while the other non-TDD run (NT1) ranked
last, and the two strict-TDD runs (T1, T2) landed safely in the middle.**

| ID | Workflow | Rank | Msgs | Impl size | Tests | 1st test run | Test failures that exposed a **code bug** | Bugs shipped |
|----|----------|------|------|-----------|-------|--------------|------------------------------------------|--------------|
| NT2 | non-TDD | **1** | 28 | 13.7 KB (1 file) | 69 (batch) | **2 failed** | **1 (future-dated batch in balance)** | 3 Low |
| T2 | TDD | 2 | 126 | dataclasses | 22 (incremental) | n/a (red-green) | 0 | Low only |
| T1 | TDD | 3 | 134 | ~133 lines, dicts | 21 (incremental) | n/a (red-green) | 0 | none |
| NT1 | non-TDD | 4 | 22 | 3.6 + 7.5 KB | 74 (batch) | **all 74 passed** | **0** | **2 High** |

> Note on the `score` field in the JSON (T1 0.95, NT1 0.85, NT2 0.88, T2 0.65):
> these are per-scenario evaluator scores measuring *adherence to that run's own
> instructions* (TDD-compliance for T-runs, testing-approach for NT-runs). They
> are **not** comparable across scenarios and do not track our quality ranking —
> do not read them as a quality signal.

---

## What each workflow actually did

**T1 / T2 (strict TDD).** Both executed a textbook red-green-refactor loop for
120–134 messages: write one test → run → confirm red → minimal implementation →
run → green → next. T1 wrote 21 tests one at a time (msgs 07–128), T2 wrote 22
the same way. Every implementation change was the *minimum* needed to pass the
test just written. The design **accreted** from these minimal steps and was
never revisited holistically — T1 ended with untyped nested dicts and a
vestigial single-element batch list; T2 landed on cleaner dataclasses. Both were
**functionally correct** (no High/Med bugs). When 99% coverage was hit, T1
explicitly stopped adding domain tests and spent its last steps investigating a
single dead line (msgs 121–131) rather than probing more edge cases.

**NT1 (non-TDD, rank 4).** Planned the package up front (msg 03), then wrote
`models.py`, `engine.py`, and a single 26 KB test file with **74 tests in one
shot** (msgs 06–14). Ran the suite once: **all 74 passed on the first attempt**
(msg 16–17). Checked coverage (98%), declared done. The tests never disagreed
with the code even once.

**NT2 (non-TDD, rank 1).** Opened with an explicit whole-system "## Design Plan"
(msg 01), then wrote the largest, most complete implementation of the field
(13.7 KB, with input validation, docstrings, exceptions) plus a 27.8 KB / 69-test
suite up front (msgs 05–12). Ran the suite: **2 tests failed** (msg 14). The
agent then reasoned through both failures (msgs 15, 21):
- Failure #1 was a **bad test** — its two purchases were both in the signup
  month, so neither could expire; the agent recognized the test data was wrong
  and fixed the test.
- Failure #2 exposed a **real implementation bug**: *"`get_balance` as-of query
  includes future point batches because `PointBatch.is_expired` doesn't filter
  by `earned_date <= as_of`"* (msg 21). The agent fixed the implementation.

That second fix is the crux of the whole result: **the bug NT2 caught and fixed
is the exact class of bug that NT1 shipped uncaught** (NT1's rank-4 High-severity
"balance/spend count future-dated batches"). Same workflow family, opposite
outcome — decided by whether the test suite happened to disagree with the code.

---

## Hypotheses

### H1 — Holistic up-front design produced better architecture; TDD's "don't design up front" actively suppressed it
The TDD prompt explicitly instructed: *"Work through the rules… one behavior at
a time, rather than trying to design the whole system up front"* and *"write the
minimum implementation."* The non-TDD prompt said *"Build this however you think
is best designed."* The traces show the effect directly: NT2 and NT1 both began
with a whole-system design plan (NT2 msg 01, NT1 msg 03) and produced richer data
models, input validation, docstrings, and typed exceptions — **none of which any
single test demands**, so a strictly test-driven process would never generate
them. T1's design, by contrast, is the sum of 21 locally-minimal edits and never
got a holistic pass (untyped dicts, dead vestigial list). **The best-designed
solution won because its workflow permitted design; TDD's instruction to avoid
up-front design capped architectural quality.**

### H2 — The decisive event was a test *failing against a finished implementation* and revealing a code bug — and only NT2 had one
Ranking the four runs by "did a test failure ever expose a genuine
*implementation* bug (not just a not-yet-written feature)?" reproduces the
quality ranking's top and bottom exactly:
- **NT2 (rank 1):** yes — 1 real bug caught + 1 bad test caught (msgs 15, 21).
- **NT1 (rank 4):** no — 74/74 green on first run; zero disagreement; 2 High bugs shipped.

In strict TDD (T1/T2) tests *do* fail constantly, but always **by construction**:
the test is written moments before the code that exists only to satisfy it. The
red is guaranteed and carries no new information about a *completed* design — it
just drives the next minimal edit. So TDD's red-green produced correctness on the
narrow behaviors each test named, but never surfaced a cross-cutting design bug,
because no test was ever run against a system the author considered finished.

### H3 — All-green-on-first-try is a warning sign, not a success (the NT1 vs NT2 differentiator)
Both non-TDD runs wrote a large test suite up front against a just-written
implementation. The difference: NT1's tests **all passed immediately**, NT2's
did not. When the same author writes code and tests from one mental model in one
sitting, the tests encode the *same assumptions* as the code — including the same
blind spots (chronological insertion order, no point-in-time / future-dated
queries). NT1's perfect first run means its tests were **mutually confirming**
with the code, so its two High bugs sailed through. NT2's 2 failures are evidence
its tests reached slightly *beyond* the implementation's assumptions, and that
gap is precisely where the real bug lived. **Test-code disagreement, however it
arises, is what catches bugs — and a suite that agrees with the code on the first
try has proven nothing.**

### H4 — Batch/holistic test authoring yielded broader rule coverage than incremental TDD
The up-front suites were far larger (NT2 69 tests / 27.8 KB, NT1 74 / 26 KB) than
the incrementally grown TDD suites (T1 21, T2 22). Designing tests holistically
pushes the author to enumerate the full rule matrix at once; incremental TDD tends
to stop when the coverage threshold is met — T1 literally halted at 21 tests once
99% coverage was reached and spent its remaining effort on a dead line rather than
new domain edges. Breadth alone isn't sufficient (NT1 was broad but not
adversarial), but combined with H2/H3 it gave NT2 both reach and a real check.

### H5 — TDD reduced variance; non-TDD increased it (so "non-TDD is better" is the wrong lesson)
The honest reading of the spread: **both TDD runs were correct-but-middling**
(no functional bugs, unremarkable design), while the **non-TDD runs occupied both
the top and the bottom** — highest ceiling *and* lowest floor. TDD behaved like a
safety rail: it guaranteed each named behavior was tested and correct, at the cost
of design ambition and broad edge coverage. Non-TDD removed the rail: given room
to design and write comprehensive tests, NT2 excelled — but NT1, with the same
freedom and a suite that never challenged its code, shipped the worst solution.
NT2 won partly on the good fortune that its test suite contained a point-in-time
consistency check that its implementation failed.

---

## Conclusion

The non-TDD workflow produced the best solution for two compounding reasons
visible in the traces:

1. **It was allowed to design the whole system first** (H1), which is where
   NT2's superior architecture — validation, clean model, docstrings — came from.
   The TDD prompt's "one behavior at a time, minimum implementation, don't design
   up front" structurally prevented its runs from reaching that quality.
2. **Its tests genuinely disagreed with its implementation** (H2/H3). NT2 wrote a
   broad suite up front, ran it against a completed design, hit 2 red tests, and
   in fixing them caught a real bug (the future-dated-batch defect) that its
   TDD-safe and non-TDD-unlucky peers never surfaced.

But the result should not be read as "non-TDD beats TDD." The controlled
comparison shows **higher variance, not higher mean**, for non-TDD (H5): the same
workflow that produced the winner also produced the loser. The transferable
lessons are workflow-agnostic:

- **Let the agent design holistically before locking in behavior-by-behavior** —
  or TDD will cap the architecture.
- **Treat an all-green first test run as a red flag**, not a win: it usually means
  the tests only encode what the code already assumes.
- **Deliberately write tests that can disagree with the implementation**
  (point-in-time queries, out-of-order input, boundary and "impossible" states) —
  the single bug that decided this ranking was caught by exactly such a test.
