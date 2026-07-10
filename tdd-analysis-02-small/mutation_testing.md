# Mutation Testing: Gap Analysis

Deep-dive on `mutmut` results for all four `slot_validator` codebases (same task, two built
TDD-first, two built non-TDD — see [`README.md`](README.md) for the run comparison). Each
codebase was mutated in isolation (`source_paths = ["slot_validator"]`, isolated `.venv`),
survivors were inspected individually with `mutmut show <id>`, and cross-checked against the
actual test files.

## Ranking

| Rank | TDD used? | Codebase | Total Mutants | Killed | Survived | Mutation Score |
|---|---|---|---|---|---|---|
| 1 | Yes | `sol-2026-07-09_11-42-10/` | 110 | 103 | 7 | 93.6% |
| 2 | Yes | `sol-2026-07-09_10-47-37/` | 117 | 109 | 8 | 93.2% |
| 3 | No | `sol-2026-07-09_11-59-54/` | 209 | 193 | 16 | 92.3% |
| 4 | No | `sol-2026-07-09_11-55-41/` | 173 | 155 | 18 | 89.6% |

Note on mutant counts: `sol-2026-07-09_11-59-54` produces far more mutants (209) than the other
three (~110-175) for the same task because its implementation is split into five small
`_validate_*` helper functions plus the dispatcher, which gives mutmut more distinct AST nodes to
mutate than the other codebases' more monolithic single-function implementations. Raw survivor
counts are therefore not directly comparable across codebases — the **score** (killed/total) is
the fair comparison axis, which is why the ranking above uses it.

## Cross-cutting patterns

These gap *shapes* recur across all four codebases regardless of TDD/non-TDD origin — they're
properties of how people naturally write assertions against a "valid / error_field / error_reason"
result object, not properties of the workflow used to build the code.

**1. `error_reason` / message text is essentially never asserted precisely.**
This is the dominant pattern everywhere: 15 of 18 survivors in `sol-2026-07-09_11-55-41`, 6 of 16
in `sol-2026-07-09_11-59-54`, 3 of 8 in `sol-2026-07-09_10-47-37`, and 4 of 7 in
`sol-2026-07-09_11-42-10` are message-string mutations (deleted to `None`, upper/lowercased, or
marker-wrapped) that survive because tests assert only `valid is False` and `error_field == "..."`,
or at most a case-insensitive substring of the reason. This is a genuine, cheap-to-fix test gap in
every codebase, but it is a **low-severity** one: it means a diagnostic string could regress
silently, not that classification logic (valid/invalid) is wrong.

**2. Off-by-one string-slicing on time parsing, masked because tests never use minutes with a
non-zero tens digit and zero units digit.**
Two independent codebases (`sol-2026-07-09_11-42-10` mutant `_36`, and `sol-2026-07-09_11-55-41`
mutant `_66`) have the exact same latent gap shape: `int(time_str[2:])` mutated to
`int(time_str[3:])`, silently reading only the last digit of the minute. Because both suites only
ever use minutes `00, 15, 30, 45` (never `10, 20, 40, 50`), the corrupted single-digit minute
happens to fall on the same side of the `mm not in (0, 30)` check as the correct two-digit value in
every tested case. This is the single most **safety-critical** gap shape found in the whole
analysis — see "Overall observations" below.

**3. Boundary values tested "near" the edge but not exactly at it.**
`sol-2026-07-09_10-47-37` (`hh*60+30` upper-bound arithmetic), `sol-2026-07-09_11-55-41` (`hh > 23`
boundary), and `sol-2026-07-09_11-59-54` (`hh > 23` / `mm > 59` boundaries) all have survivors that
trace back to testing round numbers (`1730`, `1800`, `2530`) instead of the exact integer boundary
(`23:xx`, `24:xx`, minute `59` vs `60`). In `sol-2026-07-09_11-59-54` this pattern produced the one
survivor across all four codebases that actually **misclassifies a valid input** under mutation
(`hh > 23` → `hh >= 23` rejects the legitimately valid `23:30`).

**4. Layered/redundant validation masks boundary and operator mutations.**
Several validators re-check timing/format constraints at more than one layer (a specific check,
then a broader range check later). When a mutant weakens the first check, the second still catches
the bad input and returns the same `error_field`, so the *classification* doesn't change and only
the *reason text* differs — invisible under pattern #1. Examples: `sol-2026-07-09_10-47-37`
mutant `_98` (checksum length check `or`→`and`, caught downstream by the numeric mismatch check);
`sol-2026-07-09_11-59-54` mutant `_22` (`hh>23 or mm>59` → `and`, caught downstream by the
08:00–17:30 range check).

**5. Genuine equivalent mutants exist and were verified, not just assumed.**
- `sol-2026-07-09_10-47-37` mutants `_57`/`_58`: the upper time bound `17*60+30` mutated to
  `17*61+30` / `17*60+31`. Given the codebase's own invariant that `minutes ∈ {0, 30}` (enforced
  earlier), exhaustive enumeration over all reachable `(hours, minutes)` pairs shows no value ever
  lands in the newly-opened `(1050, 1067]` or `(1050, 1051]` range — these are true equivalent
  mutants, unkillable without first changing the granularity check.
- `sol-2026-07-09_11-55-41` mutant `80` (`hh > 23` → `hh > 24`): `hh` in `24..99` is already
  rejected identically by a later range check regardless of this mutation, with no test able to
  distinguish the two even by message text (no test reaches that exact line/value combination) —
  equivalent for classification purposes.

These should not be counted as missing tests; only the "real gap" clusters below represent
actionable test-suite improvements.

## Per-codebase detail

### 1. `sol-2026-07-09_11-42-10` (TDD) — 93.6% (103/110)

Single-file implementation, all logic in `slot_validator/__init__.py`.

| Section | Lines | Survivors |
|---|---|---|
| Format/segment-count check | 9-11 | 3 (`_11, _12, _13`) |
| DAY check | 15-16 | 0 |
| TIME format (regex `\d{4}`) | 18-19 | 0 |
| TIME parse (hh/mm split) | 21 | 1 (`_36`) |
| TIME minutes-on-half-hour check | 22-23 | 0 |
| TIME business-hours range check | 26-28 | 3 (`_46, _58, _59`) |
| ROOM regex/prefix | 30-32 | 0 |
| Checksum computation/compare | 35-46 | 0 |

**Most significant finding — mutant `_36`** (`__init__.py:21`, `int(time[2:])` → `int(time[3:])`):
silently reads only the last minute digit. `validate("FRI-1730-IC12-45")` under the mutant computes
`mm=0` instead of `30` — both land inside the valid time band, so the existing pass/fail tests
can't tell the difference; `validate("MON-0815-GP1-55")` gives `mm=5` instead of `15` — both are
`not in (0, 30)`, so both trigger the identical generic message. No test asserts the parsed minute
value itself. Suggested test: a time with a non-zero tens digit and zero units digit, e.g.
`"MON-0940-GP1-55"` (mutant would compute `mm=0`, wrongly passing the granularity check).

- **Cluster — format-error text case/marker mutations** (`_11, _12, _13`, line 11): survive because
  the existing assertion is `"format" in reason.lower()`, true under all three mutations.
- **Cluster — upper business-hour boundary arithmetic** (`_46, _58, _59`, lines 26-27): suite only
  probes `1730` (valid) and `1800` (invalid); nothing between `1051`–`1079` minutes (e.g. `"1740"`)
  is tested, which is exactly where `_58`/`_59`'s widened bound would wrongly accept. `_46`
  (`hh*60+mm`→`hh*60-mm`) is weaker to fully kill with one test — needs a half-hour time where `+mm`
  and `-mm` diverge across the boundary.

No equivalent mutants in this codebase's survivor set; all 7 are real, fixable gaps.

### 2. `sol-2026-07-09_10-47-37` (TDD) — 93.2% (109/117)

Single-file implementation, `slot_validator/validator.py`, function `validate`.

| Section | Lines | Survivors |
|---|---|---|
| Format (segment count) | 9-11 | 3 (`_11, _12, _13`) |
| Day validation | 15-16 | 0 |
| Time format check | 18-19 | 0 |
| Time minute-parsing | 21-22 | 1 (`_35`) |
| Time-of-day bounds | 26-28 | 3 (`_45, _57, _58`) |
| Room pattern/prefix | 30-36 | 0 |
| Checksum format/comparison | 38-45 | 1 (`_98`) |

- **Cluster — format-error message text unchecked** (`_11, _12, _13`, line 11): only branch in this
  codebase without any substring assertion on the error message; every other branch has one.
- **Cluster — minute off-by-one slicing** (`_35`, line 22, `time_str[2:]`→`time_str[3:]`): same bug
  shape as `sol-2026-07-09_11-42-10`'s `_36` and `sol-2026-07-09_11-55-41`'s `_66` — confirmed real
  via direct computation (`"0810"` → correct `mm=10` rejected; mutant `mm=0` wrongly accepted).
- **Cluster — time-bounds arithmetic, split verdict** (`_45, _57, _58`, lines 26-27): `_45`
  (`hours*60+minutes`→`hours*60-minutes`) is real — `08:30` is misclassified as invalid under the
  mutant, and no test covers a half-hour time near the lower boundary. `_57`/`_58` are **verified
  equivalent mutants** (see cross-cutting pattern #5).
- **Cluster — checksum length check `or`→`and`** (`_98`, line 41): masked because the fallback
  numeric-mismatch check produces a different message but the same `error_field`, and the existing
  test only substring-checks for `"CHECKSUM"`.

2 of 8 survivors are equivalent mutants; 6 are real, fixable gaps.

### 3. `sol-2026-07-09_11-59-54` (non-TDD) — 92.3% (193/209)

Implementation split into `_validate_day`, `_validate_time`, `_validate_room`,
`_validate_checksum`, `_alphabet_position`, dispatched by `validate_slot_code`.

| Function | Survived / total relevant |
|---|---|
| `validate_slot_code` | 1 |
| `_validate_day` | 2 |
| `_validate_time` | 9 (56% of all survivors) |
| `_validate_room` | 2 |
| `_validate_checksum` | 2 |
| `_alphabet_position`, `_validate_format` | 0 (fully killed) |

- **Cluster — `error_reason` text never asserted** (`_validate_day` `_10, _13`; `_validate_room`
  `_11, _14`; `_validate_checksum` `_9, _12`; `validate_slot_code` `_11` for the `TypeError` message
  type-name): 7 survivors, all the standard weak-assertion pattern.
- **Cluster — `_validate_time` boundary/operator mutations masked by the downstream 08:00–17:30
  range check** (`_9, _12, _22, _24, _25, _26, _29, _32`): the clock-validity check (`hh>23 or
  mm>59`) sits before a broader range check sharing the same `error_field="TIME"`; most mutations
  here only change the *reason text*, not the classification, because the later check re-catches
  the bad input.
- **Most behaviorally significant survivor in this codebase — `_validate_time` mutant `_23`**
  (`hh > 23` → `hh >= 23`, line ~85): this one is **not** message-only — it actually
  misclassifies the legitimately valid time `23:30` as invalid, because no test in the suite uses
  an hour of exactly `23` (tests use `1730, 1800, 0730, 0800, 0000, 0915, 0960, 2530`). This is the
  single sharpest test gap found across all four codebases.

No equivalent mutants identified in this codebase's survivor set (every mutation was confirmed to
change either the reason text or, in one case, the classification).

### 4. `sol-2026-07-09_11-55-41` (non-TDD) — 89.6% (155/173)

Single-file implementation, `slot_validator/validator.py`, function `validate_slot_code` plus
helpers `_letter_position`, `_day_letter_sum`, `_compute_checksum` (all three helpers are
thoroughly killed — every survivor traces back to `validate_slot_code` itself).

- **Cluster A — error string mutations on the non-string-input check** (`_11, _12, _13`, line 99):
  same pattern as elsewhere; substring check `"string" in reason.lower()` survives all three
  variants.
- **Cluster B — `error_reason` replaced with `None` on six different branches** (`_33, _54, _83,
  _95, _107, _135`): day/time-format/hour-range/time-range/room/checksum branches all have this gap
  — none of the corresponding tests assert anything about `error_reason`.
- **Cluster C — degenerate AST encoding of the same gap as Cluster B** (`_36, _57, _86, _98, _110,
  _138`): mutmut generated a different-looking diff (dropped closing paren / dropped keyword arg)
  for the same six sites, but the observable effect is identical to Cluster B. These 6 + Cluster
  B's 6 are really **one underlying gap** ("`error_reason` unchecked on 6 of ~10 error branches"),
  not twelve independent ones.
- **Cluster D — `hh > 23` boundary** (`79`: `hh > 23`→`hh >= 23`; `80`: `hh > 23`→`hh > 24`):
  `79` is a real but message-only gap here (unlike its analogue in `sol-2026-07-09_11-59-54`, this
  codebase's downstream range check still rejects `hh=23` with the same `error_field`, just
  different text — because this codebase's structure re-validates range differently). `80` is a
  **verified equivalent mutant** (see cross-cutting pattern #5).
- **Cluster E — the same minute-slicing off-by-one as the other two codebases** (`66`, line ~148,
  `time_part[2:]`→`time_part[3:]`): identical root cause and identical fix to
  `sol-2026-07-09_11-42-10`'s `_36` / `sol-2026-07-09_10-47-37`'s `_35`. Highest-priority gap in
  this codebase.

1 of 18 survivors (`80`) is an equivalent mutant; the rest are real gaps, dominated by the
unchecked-`error_reason` pattern (12 of 18).

## Overall observations

**No actual bugs in shipped code.** Across all four codebases and all 49 survived mutants
combined, none reveal an implementation defect — every survivor was confirmed (either by direct
computation or by the subagent reading the surrounding logic) to be either a genuine test gap or a
verified equivalent mutant. What differs is how *safety-critical* the gap is:

- **Most severe class — the minute-slicing off-by-one** (`time[2:]`→`time[3:]`) appears
  independently in **both** TDD codebases (`sol-2026-07-09_11-42-10` mutant `_36`,
  `sol-2026-07-09_10-47-37` mutant `_35`) and in the weaker non-TDD codebase
  (`sol-2026-07-09_11-55-41` mutant `66`). All three test suites happen to only use minutes
  `00/15/30/45`, never a value with a non-zero tens digit and zero units digit (`10/20/40/50`),
  which is the only input partition that exposes it. This is the one gap shape worth fixing in
  every affected codebase, since a real one-character slicing regression would ship silently.
- **Second most severe — `sol-2026-07-09_11-59-54` mutant `_23`** (`hh > 23`→`hh >= 23`) is the only
  survivor across the entire analysis that actually **misclassifies a valid input** (`23:30`)
  rather than just losing message fidelity — worth calling out as the single sharpest individual
  gap found.
- Everything else reduces to the two cheap, mechanical patterns described in cross-cutting #1 and
  #3 (message text unchecked; boundaries tested loosely rather than at the exact edge).

**Mutation score vs. the earlier quality comparison.** [`README.md`](README.md)'s "Comparison
results" section notes that when Opus was asked to compare test/solution quality across these same
runs by other means, it ranked the two **non-TDD** runs first. Mutation testing here produces the
**opposite** ordering on this axis: both TDD codebases (93.6%, 93.2%) score above both non-TDD
codebases (92.3%, 89.6%), and the weakest codebase overall (`sol-2026-07-09_11-55-41`, 89.6%) is
non-TDD. The gap between TDD and non-TDD mutation scores here is modest (roughly 1–4 points) and
is driven almost entirely by the same generic "message text unchecked" pattern in all four
codebases rather than by TDD-specific coverage discipline — so this shouldn't be read as strong
evidence that TDD produces categorically more mutation-resistant tests, only that it didn't
underperform on this metric the way the other comparison suggested it might. The higher raw
mutant count in `sol-2026-07-09_11-59-54` (209 vs. ~110-175 elsewhere) reflects implementation
style (more, smaller functions) rather than test quality, reinforcing that mutation *score* rather
than raw survivor count is the right cross-codebase signal.
