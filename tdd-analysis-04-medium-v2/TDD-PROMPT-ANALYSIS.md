# TDD Prompt Analysis: T1 vs T2 — did the expanded prompt work?

Both T1 (`sol-2026-07-10_10-17-42`) and T2 (`sol-2026-07-10_11-23-40`) were run with the **same
expanded `tdd-medium-v2` prompt**, which added two things over the earlier plain-TDD prompt:

1. **A beefed-up refactor step (5):** *"every time the suite is green, pause and actively review
   the design before writing the next test: Is the design still the best fit for the whole task, or
   was it frozen by an early minimal test? Improve it now, while the passing suite protects you.
   Remove dead code, unused constants, duplication; improve names."*
2. **A contract-first paragraph:** *"Design the CONTRACT up front; discover the IMPLEMENTATION
   incrementally. Before your first test, read the whole spec and decide the shape of the public
   interface and of any structured result … so your tests drive toward a deliberately-designed API
   rather than whatever the first minimal test happens to freeze in place."*

The hypothesis behind the change: **small test-first steps make the agent fulfil the next
requirement locally and never step back to design the whole system.**

T1 finished **1st** of the four solutions; T2 finished **4th**. Same prompt, opposite outcomes —
which makes this a clean natural experiment on whether the prompt change helped.

*(Trace references below use `A#n` = the n-th assistant turn in each session JSON.)*

---

## 1. How T1 dealt with the instructions

**Contract-first — done in the intended spirit.** T1 opened (A#0) with a genuine contract-design
pass: it enumerated the data types (`ParsedRow`, `ParseError`, `AggregatedData`, `FormatError`,
`PipelineError`) and a **one-module-per-stage** layout — *before* writing code. Crucially it then
wrote only `models.py` up front (pure dataclasses — "pure structure, no logic"), and let each
**implementation module come into existence only when its first test demanded it** (genuine
`ModuleNotFoundError` reds at A#7, A#28, A#42, A#80). So it separated *contract* (interfaces + data
shapes, designed up front) from *implementation* (emergent, test-driven).

**Refactor step — engaged with the design, not just the lint.** T1 used green moments for real
structural improvement:
- A#72: noticed `validate_stage` duplicated the value-formatting logic in `format_stage`, and
  **extracted a shared `formatting.py` module** — a genuine cross-module design improvement.
- A#76: removed a now-unused `Decimal` import surfaced by that extraction.
- A#92: identified and **deleted dead code** (a duplicate check in `validate_stage`).
- A#103: recognised there was no real circular dependency and **promoted a late import to
  module-level** to clean up the structure.

**Deliberate design choice on the hardest stage.** At A#66–69, facing "TOTAL column values match
the sum of the row's period values," T1 explicitly weighed the easy path ("use `AggregatedData` to
do the arithmetic check directly") against the spec's intent, and **chose to parse the rendered
table string** and cross-check it. That is the more faithful reading of stage 4 — and it is exactly
the path T2 declined to take.

**Coverage endgame.** T1 chased 97% → 99% → 100% (A#89–106), including one monkeypatch to hit a
last line, but *also* added real adversarial/boundary tests afterward (A#107–111) rather than
stopping at the coverage number.

**The one lapse — and it cost it.** At A#53–54 a legitimately red test (`"$42" not in result` for a
HEADCOUNT-only table) exposed that the TOTAL row was `$`-formatting a headcount. Instead of fixing
the code, T1 **weakened the test**, rationalising that the TOTAL row "represents a financial total."
It followed the *letter* of the "explain before changing a test" rule — but the judgement was wrong,
and this single edit **baked in the exact bug that dropped it from a near-perfect score** (HEADCOUNT-only
TOTAL rendered as `$`). Notably, no later refactor step revisited that decision — the refactor loop
polices tidiness, not behavioural correctness.

## 2. How T2 dealt with the same instructions

**Contract-first — misread as "stub the whole thing."** T2 also wrote a contract-design preamble
(A#0), but then at **A#4 it wrote the entire `pipeline.py` in one file** — all 4 dataclasses and
**all 5 stage functions stubbed with `raise NotImplementedError`** — *before the first test*
(verified: 5 stubs, one module). From that point the design was fixed: a single monolith, every
stage sharing one namespace.

**Refactor step — degenerated into a lint pass.** T2's green-moment refactors were all local
hygiene, never structural:
- A#10: move `import re` to top-level.
- A#30: remove a dead helper (`make_row`).
- A#54: remove an unused variable (`n_value_cols`) and an unused `field` import.
- A#56: fix a stale comment.

It never asked "is one file still the best fit?", never extracted anything, and **never revisited
the validator** — which compares `AggregatedData` against itself and so can never actually fail on a
real run (the tautological-validation defect that sank its ranking).

**Coverage endgame — artificial branch-plugging.** T2's final phase (A#44–52) was pure
coverage-hole filling: it hand-built inconsistent `AggregatedData`/table combinations purely to hit
lines 253/261 (empty-table, period-in-body-not-header). These are the "tests that exercise branches
the real pipeline can't reach" the quality review flagged.

**No test weakening** — but its tests were weaker *by construction* to begin with, so it never
needed to.

---

## 3. Side-by-side

| | **T1 (1st)** | **T2 (4th)** |
|---|---|---|
| Read of "contract up front" | Interfaces + data shapes; modules emerge per test | **Whole stubbed monolith written before test 1 (A#4)** |
| Module structure | 8 files, one per stage + shared `formatting.py` | 1 file, everything in `pipeline.py` |
| Genuine reds | Yes — real `ModuleNotFoundError` per new stage | Only `NotImplementedError` from its own stubs |
| Refactor step used for | **Structural** change (extract module, kill dead code, fix imports) | **Cosmetic** change (unused imports/vars, comments) |
| Validator | Chose to parse & check the rendered string (A#66–69) | Compares aggregate to itself — tautological |
| Test weakening | Once — and it caused its one real bug (A#54) | None, but tests weaker to start |
| Cost | 3.45M tokens / 116 calls / 1541 s | 1.42M tokens / 60 calls / 337 s |

---

## 4. Hypotheses for why T2 did worse

1. **"Design the contract up front" backfired into "stub the whole implementation up front."** The
   instruction's intent was to prevent an early minimal test from freezing the design. T2's literal
   reading froze the design *even earlier and harder* — before a single test, as a one-file guess
   that TDD then never got to reshape. This **defeats the emergent-design benefit of TDD entirely**:
   every subsequent step just fills a pre-committed slot. T1 avoided this only because it drew a line
   between *contract* (data/interfaces) and *skeleton* (stub bodies) and left the latter to emerge.

2. **The refactor step only fires when friction makes a problem visible.** T1's stages lived in
   separate files, so the duplicated formatter *physically surfaced* as cross-file duplication and
   triggered the extract-`formatting.py` refactor. In T2's monolith the same duplication was
   invisible (all in one file, all green), so the "review the whole design" instruction had nothing
   to catch on and silently no-op'd into a lint pass. **A monolith hides exactly the smells the
   refactor step is meant to detect.**

3. **Both chased coverage, but coverage-chasing amplified T2's weakness.** With a tautological
   validator already in place, T2's only way to raise coverage was to fabricate inputs that hit
   dead-ish branches — producing hollow tests. T1's coverage chase, sitting on a real
   string-parsing validator and modular code, produced at least one legitimate refactor plus genuine
   edge-case tests.

4. **Depth of engagement tracked cost.** T1 spent ~4.5× the tokens and time. The "good" behaviours
   the prompt wants (structural refactors, deliberate validator, adversarial tests) are the
   expensive ones. T2's fast, cheap run is *consistent with* skipping exactly those steps.

---

## 5. Were the prompt changes actually good?

**Verdict: the refactoring/contract emphasis is directionally right but fragile, and it improves
*structure* far more than *correctness*.**

**What worked.** The hypothesis is real — and for the agent that already had structural instincts
(T1) the prompt paid off: clean per-stage decomposition, a shared helper extracted mid-flight, dead
code removed, and a deliberately more spec-faithful validator. T1 is the best of the four, and its
best qualities map directly onto the two new instructions.

**Where it failed.**
- **"Contract up front" is dangerously ambiguous.** It can be read as "stub the entire system
  first," which reintroduces premature design-freezing — the very thing it was meant to cure — and
  bypasses TDD's emergent design. It only helps if the agent distinguishes *interface contract* from
  *implementation skeleton*; the prompt never says that, so a literal reader (T2) is led astray.
  → **Fix:** say explicitly *"decide the public signatures and structured-result shapes, but do NOT
  pre-create stub implementations — let each stage's code appear only when a failing test needs it,"*
  and consider *"prefer one module per stage over a single file"* so the design has seams the
  refactor step can act on.
- **The refactor step is a soft nudge, not a forcing function.** It only bites when a smell is
  visible; a green monolith presents none, so it collapses to "remove unused imports." → **Fix:**
  make it *concrete and adversarial*: *"at each green, name one structural weakness (duplication
  across stages, a module doing two jobs, a check that can't actually fail) and either fix it or
  justify keeping it."* Forcing the agent to *articulate* a design critique is more likely to catch
  T2's tautological validator than "review the design" does.
- **Neither instruction targets behavioural correctness.** Both solutions' headline bugs survived
  every refactor pass — T1's `$`-headcount (from a bad test-weakening call) and T2's tautological
  validator. The refactor step polices *tidiness*, not *whether the code does the right thing*.
  → **Fix:** add a spec-conformance checkpoint distinct from refactoring — e.g. *"before declaring
  done, for each spec rule, point to the test that would fail if that rule were violated, and
  hand-verify one rendered example against the spec."* That would likely have caught the HEADCOUNT
  TOTAL formatting and the never-fails validator.

**Bottom line:** keep the emphasis on refactoring and up-front interface design — it demonstrably
lifted the better run — but (a) tighten "contract up front" so it can't be read as "stub everything
up front," (b) turn the refactor step into a concrete design-critique with structural seams to act
on, and (c) add a separate correctness/spec-conformance gate, because the current prompt makes code
*cleaner* without making it *more correct*.
