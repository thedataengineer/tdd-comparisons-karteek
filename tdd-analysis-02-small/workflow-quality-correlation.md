# Workflow vs. Quality: Did TDD Help or Hurt?

A follow-up analysis correlating **how** each of the four solutions was built (reconstructed
from the agentic session traces) with the **quality** ranking from the earlier comparison.

The surprise that prompted this: the two runs instructed to use **strict TDD ranked 3rd and
4th**, while the two **non-TDD runs ranked 1st and 2nd**. This report examines whether that's
a real workflow effect, and proposes causal mechanisms.

> ⚠️ **Sample-size caveat up front:** n = 2 per arm, one small fully-specified task, one model
> (`claude-sonnet-4-6`). This is a *hypothesis-generating* case study, not a statistically
> significant result. Treat everything below as "plausible mechanisms worth testing at scale,"
> not "TDD is bad."

---

## The correlation at a glance

| Rank | Solution | Workflow | Result type | Tests | Turns | Tokens | Duration | Key defect |
|:----:|----------|----------|-------------|:-----:|:-----:|:------:|:--------:|------------|
| 🥇 1 | `11-55-41` | **Non-TDD** | `ValidationResult` dataclass | 61 | 10 | 122K | 102s | none (nits only) |
| 🥈 2 | `11-59-54` | **Non-TDD** | `ValidationResult` dataclass | 58 | 10 | 118K | 101s | Unicode `\d` leniency |
| 🥉 3 | `11-42-10` | **TDD** | bare dict + free-text `reason` | 21 | 55 | 894K | 215s | dead constant; thin design |
| 4 | `10-47-37` | **TDD** | bare dict + free-text `error` | 20 | 68 | 1.14M | 237s | **crash bug** on Unicode digit |

Two clean clusters emerge, and workflow is the dividing line on **every** axis: design richness,
test count, defect severity, and cost. Notably, the non-TDD runs achieved their higher quality
with **~8× fewer tokens and ~6× fewer turns**.

Both prompts shared the identical task and the identical **80% coverage target** — the *only*
manipulated variable was the test-first mandate. And all four hit 100% line coverage, so coverage
did not discriminate; **workflow did.**

---

## What the traces actually showed

### Non-TDD runs (ranked 1–2): design-first, single-pass
Both sessions followed the same shape:
1. Read the whole spec, **decide the architecture up front** (in an opening thinking block).
2. Write the complete implementation in **one `Write`**.
3. Write **all** tests in one `Write`.
4. Run pytest once or twice, confirm 100% coverage, done.

Critically, both mapped the spec sentence *"a structured result indicating whether the code is
valid and, if not, which specific rule failed and why"* directly onto a three-field dataclass:

```python
@dataclass
class ValidationResult:
    valid: bool          # whether
    error_field: str     # which rule   (machine-readable)
    error_reason: str    # why          (human-readable)
```

This was never deliberated incrementally — it appears fully formed in the first and only version
of the file. Holding the entire spec in mind at once is what produced the richer, machine-branchable
result type.

### TDD runs (ranked 3–4): emergent design, minimal-code-to-pass
Both followed a genuine, disciplined red-green loop (the traces show honest "Red ✓ / Green ✓"
narration and even a self-correction where a trivially-passing test was rewritten). But two
structural consequences of the loop shaped the outcome:

- **The result shape was locked in by the *first* test.** That test only asserted
  `isinstance(result, dict)` and `"valid" in result`. Under "minimal code to pass," a bare dict is
  all that was ever built — and later tests only asserted `"DAY"/"TIME" in result["error"]`
  (substring checks), so a **free-text error string was always sufficient to stay green**. No test
  ever demanded a machine-readable field, so the richer design never emerged.
- **The refactor step was a perpetual no-op.** Because each minimal edit left the suite green,
  "refactor if needed" never triggered a cleanup pass. Result: `11-42-10`'s dead
  `VALID_ROOM_PREFIXES` constant survived, and neither run ever elevated the dict toward a
  structured type.

### The crash bug (`10-47-37`) is the sharpest illustration
The `isdigit()`-guard-then-`int()`-convert pattern was introduced as the *minimal code* to pass a
single test whose invalid input was `"MON-08AB-GP1-49"` — **ASCII letters**. `isdigit()` rejects
ASCII letters, so that one test fully green-lit the guard. Every one of the ~17 test inputs in the
suite is pure ASCII, so the gap between `"²".isdigit()==True` and `int("²")→ValueError` was never
turned into a test. **100% line coverage reported "done" while an entire test *category* was
missing** — coverage can't see a missing input class.

---

## Hypotheses (with confidence levels)

**H1 — Strict "minimal-code-to-pass" suppresses up-front design richness. (High confidence)**
The single biggest quality gap between clusters is the result type (dataclass vs. bare dict), and
the traces show this is a direct artifact of TDD: the first test fixed the shape as a dict, and
minimalism kept it there. The spec explicitly rewarded a structured result, so the design-first
runs that read the whole spec first scored higher on design. *Causal, not just correlational — the
mechanism is visible in the traces.*

**H2 — TDD's refactor step degrades to a no-op when every increment is already green. (High
confidence)**
Neither TDD run performed a substantive refactor; the dead constant and the un-elevated design both
survived because nothing ever forced a step-back. The "green after every tiny edit" cadence may
actively suppress the "step back and harden/clean up" reflex.

**H3 — Both workflows share a blind spot; TDD's incrementalism gave *false* confidence about it.
(Medium-High confidence)**
The Unicode-digit edge was missed by **three of four** runs (both TDD as a crash risk, one non-TDD
as silent leniency). Tests in every case were derived from the *same mental model* as the code, so
an edge absent from that model was absent from both. TDD didn't help here — the agent only writes
tests for behaviors it consciously thinks of, and 100% coverage made the loop *feel* exhaustive
when a whole input class was untested. (The best run, `11-55-41`, avoided the bug by luck of a more
defensive implementation, not by a Unicode test.)

**H4 — For a small, fully-specified task, design-first is both cheaper and higher quality. (Medium
confidence)**
Non-TDD delivered better results at ~8× lower token cost and ~6× fewer turns. When requirements are
fully known up front, the incremental loop spends turns re-deriving structure one rule at a time
with no compensating quality gain. *This is likely task-dependent (see confounds).*

**H5 — Coverage-as-done-signal is misleading in both arms, but especially masks TDD's gaps.
(Medium confidence)**
All four monitored coverage and all hit 100%. Yet coverage was blind to: the crash-inducing input
class, the Unicode leniency, redundant tests (three identical `1800` tests in `11-59-54`), and
design thinness. A coverage target satisfied trivially provided false assurance in every run.

**H6 — The test-count advantage of TDD is partly illusory. (Low-Medium confidence)**
Counterintuitively the *non-TDD* runs wrote **more** tests (58–61 vs. 20–21). Writing tests against
a finished design let them systematically enumerate one case per branch across organized test
classes. `11-42-10`'s final 10 tests were batch-added *after* coverage already hit 100% —
confirmatory padding, not behavior-driving. So TDD produced *fewer, earlier* tests here, not more.

---

## Confounds & alternative explanations (why not to over-read this)

- **Task shape favors design-first.** This is a small, closed, fully-specified rule set — the ideal
  case for holding everything in your head. TDD's real advantages (managing emergent/underspecified
  requirements, forcing decomposition of a problem you *don't* yet understand) don't get to shine
  here. **The result may well invert on an open-ended or exploratory task.**
- **Confounded variable: is it "TDD" or "emergent design"?** The causal lever the traces expose is
  specifically *first-test-fixes-the-shape* + *minimal-code* + *refactor-as-no-op*. A TDD run that
  spent an explicit up-front design step (allowed by the prompt's "it's fine to revisit and
  refactor") before entering the loop might have captured both benefits. The mandate as written
  discouraged that.
- **Design gap vs. defect gap.** The 1-vs-3/2-vs-4 ranking is driven mostly by the **design** axis
  (dataclass vs dict), which is the strongest, clearest effect. The specific defects (crash vs.
  Unicode leniency) are the *same class* of miss and are somewhat incidental — don't over-weight the
  crash bug as "TDD causes bugs."
- **n = 2, single model, single task, single sitting.** No statistical claim is supportable.
- **A different evaluator disagreed.** The harness's own self-evaluation scored the TDD run
  `10-47-37` at 0.92 (pass). The "4th of 4" ranking is from the stricter external review. Evaluator
  choice materially affects the verdict.

---

## Bottom line

For this task, there is a **strong, mechanistically-explained correlation**: the TDD mandate, *as
written*, pushed both agents toward an emergent bare-dict design and a no-op refactor phase, while
the freedom of the non-TDD prompt let both agents design the richer `ValidationResult` up front —
faster, cheaper, and higher quality.

The most defensible causal claim is narrow: **strict "one test at a time / minimal code to pass"
optimizes for process fidelity and line coverage, but on a small fully-specified task it actively
suppresses up-front design and meaningful refactoring — the two things this task rewarded most.**
It is *not* supported to conclude "TDD produces worse code" in general; the likely lesson is that
**TDD's benefits are task-dependent**, and that **coverage is a poor proxy for quality in every
workflow** — it certified all four as "done" while missing a crash bug, a spec deviation, dead code,
and duplicate tests.

### If you wanted to test these hypotheses properly
1. Add an **underspecified/exploratory** task where design must emerge — predict TDD *wins* there (tests H4).
2. Add a **"design-first, then TDD"** arm — predict it captures both benefits (tests the H1 confound).
3. Add **adversarial/mutation testing** as the quality gate instead of coverage — predict it exposes the shared blind spot (H3/H5) regardless of workflow.
4. Increase n and vary the model before drawing any general conclusion.
