# Process → Quality: Correlation Analysis

**Question:** Does the development process used to create a solution (strict TDD,
test-first, or no process instruction) correlate with the quality of the
resulting code? In particular, does writing tests first lead to *better design*?

**Method:** Six solutions to the same task (`task.md`, a 4-stage report
pipeline) were first ranked for quality by independent reviewer subagents that
had **no knowledge of how each was made** (see `comparison_report.md`). Only
afterward were the session histories (the 6 JSON files) opened and mined for
process signals. This report cross-references the two.

**Caveat, stated up front:** n = 2 runs per condition. Everything below is a
hypothesis, not a finding. The patterns are strikingly consistent, but the
sample is far too small to be conclusive.

**Process labels are validated.** A separate per-session check (the
`analysis`/`supplementary` markdown reports and their scores) confirmed that
each run actually followed its assigned process — strict TDD really was a
strict red→green loop, test-first really wrote all tests before implementation,
and the no-process runs wrote tests after. Those scores are *adherence*
verifications, each against a different per-scenario rubric; they are **not** a
quality or completion metric and are not comparable across conditions, so they
are not used as a quality signal here. Their only role is to establish that this
is a genuine **process** difference, not merely a prompting difference.

---

## The headline result

| ID | Process | Quality rank | Quality /10 | Tests | Impl LOC |
|----|---------|:-----------:|:-----------:|:-----:|:--------:|
| NT1 | **No process** | 🥇 1 | 8.0 | 107 | 497 |
| TF2 | **Test-first** | 🥈 2 | 8.0 | 90 | 484 |
| NT2 | **No process** | 🥉 3 | 7.5 | 75 | 330 |
| T2 | **Strict TDD** | 4 | 6.5 | 29 | 207 |
| TF1 | **Test-first** | 5 | 6.0 | 62 | 348 |
| T1 | **Strict TDD** | 6 | 6.0 | 25 | 142 |

The headline:

**Stricter test discipline did NOT produce better design or code here — if
anything, the opposite.** The two **no-process** runs took 1st and 3rd; the two
**strict-TDD** runs took last and 4th. The original hypothesis ("TDD/test-first
→ better design") is not supported by this sample; the data leans the other way.

---

## Why each process produced what it did

The session transcripts explain the ranking with unusual clarity. The
mechanism is consistent across all six runs.

### No process (NT1 #1, NT2 #3): freedom → up-front holistic design

Both no-process runs did the same thing: **planned the entire architecture in
one long thinking block before writing any code**, then wrote all
implementation files, then wrote a comprehensive per-module test suite, then
used coverage only as a final polish.

- Because no process was imposed, the agent spent its opening reasoning budget
  **architecting all four stages, their data types, and cross-stage contracts
  at once**. NT1 even derived a shared `compute_layout()` helper reused by both
  format and validate — a design insight that only emerges when you hold the
  whole system in view.
- **Edge cases were found by reading the spec, not by writing tests.** NT1's
  first-pass parser already handled negative-COST-allowed, negative-REVENUE/
  HEADCOUNT-rejected, duplicate ROW_ID, and the awkward mixed-unit TOTAL row —
  all reasoned about before a single test existed. This is why the no-process
  parsers are the most defensive of the six.
- The **downside** showed up late: once code was written, the 80–100% coverage
  target became the objective, and both runs padded coverage on unreachable
  defensive branches. NT2's one **no-op test** (body entirely comments) and dead
  `except/continue` branches are a direct artifact of chasing 100% coverage on
  code that was already written — trading test integrity for a coverage number.

### Test-first (TF2 #2, TF1 #5): outcome depends entirely on the up-front design step

The two test-first runs are the most instructive pair — **same instruction,
opposite outcomes** — because "write tests first" does *not* by itself force
good design.

- **TF2 (#2)** paired test-first with **explicit up-front architecture**: its
  first thinking block enumerated the 4-module layout *and the inter-stage data
  contracts* (structured dicts, `Decimal` values, structured errors) before any
  code. It then wrote **87 tests across five per-module files**, which forced
  spec enumeration, and finished with a **deliberate coverage-driven
  verification pass** (read source, find gaps, add 3 targeted tests). Front-loaded
  tests and clear design reinforced each other.
- **TF1 (#5)** skipped the design step. It wrote 54 tests in one batch, dropped a
  single 400-line file, ran the suite once (green on first try), and then only
  chased coverage. Crucially, its tests **pinned shapes but not semantics**:
  `test_has_total_row` merely checks a line starts with "TOTAL", so a TOTAL row
  that renders headcount as dollars passed green. Because green came on the
  first run, **no debugging loop ever ran** — and the visible dead scaffolding
  (`# Recalculate cleanly` overwriting a whole branch, an `if False`, a `pass`
  where the width check belongs) was never cleaned up. It was the cheapest,
  fastest run (16 tool calls) and it shows.

**Hypothesis:** test-first is *design-neutral*. It amplifies whatever design
effort the agent brings. With an up-front architecture pass it excels (TF2);
without one it front-loads shape-only tests that give false confidence and ship
uncleaned code (TF1).

### Strict TDD (T2 #4, T1 #6): the tests became the spec, and the tests were narrower than the spec

Both strict-TDD runs followed the red→green→one-test-at-a-time loop almost
mechanically (89 and 95 tool calls — by far the most; ~half the session spent
re-running pytest). The transcripts are metronomic: "Test 14… red… green. Next."
And this is precisely what hurt quality:

- **No up-front design.** Design emerged test-by-test. "Write the minimum
  implementation to pass" meant data structures were the cheapest thing
  satisfying the current assertion — bare lists, ad-hoc `{"error": ...}` dicts,
  no error types. T1's 142-LOC single file is the direct result: no test ever
  *demanded* module decomposition, so none appeared. (T2 kept 5 modules only
  because the *prompt* enumerated the stages — not from any TDD-driven insight —
  and each module stayed a thin happy-path transform.)
- **Behavior existed only where a test drove it.** Both TDD parsers crash on
  malformed input (`IndexError`/`ValueError`) instead of returning a structured
  error, and neither enforces the ROW_ID "positive, unique" rule — because the
  agent wrote tests only for the cases the spec spelled out as *examples*
  (negative REVENUE, bad period, bad category) and never for structurally
  malformed input. **Strict TDD converted "spec coverage" into "test coverage,"
  and unlisted-but-required behavior simply never got written.** This is the
  single biggest cause of the low ranking, and it is the mechanism most directly
  attributable to the process.
- **Coverage-as-done capped exploration.** Both hit 96–100% coverage quickly and
  stopped (25 and 29 tests). But coverage measures *whether written lines run*,
  not *whether required behavior exists* — it can never flag a missing feature,
  because missing code has no uncovered lines. High coverage of shallow code
  created false confidence.
- **Attention went to mechanics, not spec breadth.** T2's no-op width-validation
  check arose because the test only asserted the header name appears in the
  string; the implementation just re-checked `col_name in header_line` and moved
  on. The agent was optimizing the test/coverage mechanics, not the requirement.

---

## Synthesis: what actually correlated with quality

The dividing line in this sample is **not** "tests first vs tests second." It is
**whether the agent did a holistic, up-front design + spec-reading pass**:

| Did an up-front whole-system design/spec pass? | Runs | Avg quality |
|---|---|---|
| **Yes** | NT1, NT2, TF2 | ~7.8 |
| **No** (design emerged incrementally, or skipped) | T1, T2, TF1 | ~6.2 |

- **No-process runs ranked high** because the absence of a prescribed loop *left
  room for* that up-front design pass, and because spec-reading (not tests)
  surfaced the tricky edge cases early.
- **Strict TDD ranked low** because its core rules — "no code before a failing
  test," "minimum implementation," "one test at a time" — actively **suppress**
  up-front design and make the test set an *upper bound* on implemented behavior.
  When the agent's self-authored tests are narrower than the spec (they were),
  the code is too.
- **Test-first split** because it neither forces nor forbids the design pass; the
  outcome tracked whether the agent chose to do one.

### Secondary observations

- **Test *count* didn't predict quality either** — but *depth* did. NT1 (107
  tests) was built to exercise each callable's full contract; T1 (25 tests) and
  TF1's format tests only pinned shapes. Coverage-driven test padding produced
  the two least honest tests in the whole set (NT2's no-op, TF1's shape-only
  format checks).
- **Everyone missed the same two things** regardless of process (see
  `comparison_report.md`): the semantics of the mixed-category TOTAL row, and a
  genuinely independent output-validation stage. Process didn't help here because
  the spec itself was ambiguous on the first and the invariant is "true by
  construction" on the second — neither is the kind of gap tests catch.

---

## Hypotheses to test with a larger sample

1. **The real lever is an up-front design/spec-reading pass, not test ordering.**
   A condition that explicitly instructs "design the whole system and enumerate
   spec edge cases before coding" — with *any* test policy — would outperform all
   three conditions here.
2. **Strict TDD systematically narrows implemented behavior to the agent's own
   test imagination.** Prediction: across many runs, strict-TDD solutions will
   disproportionately fail on *implied-but-not-exemplified* requirements
   (malformed input, uniqueness constraints), while happy-path behavior is solid.
3. **"Minimum implementation to pass" + coverage-as-done caps robustness.**
   Prediction: TDD runs will consistently show the smallest LOC, fewest tests,
   and earliest stopping — and coverage will hit target *before* edge-case breadth
   is explored.
4. **Test-first is design-neutral and high-variance.** Prediction: test-first
   quality will have the widest spread of the three conditions, correlated with
   whether an up-front design step happened.
5. **Coverage targets induce dishonest tests once code is written.** Prediction:
   no-op / tautological / shape-only tests cluster in runs where coverage was
   chased *after* implementation existed (NT2, TF1) rather than driven from the
   start.

*Generated from the six session histories listed in `README.md`; quality ranking
from `comparison_report.md` was produced blind to process.*
