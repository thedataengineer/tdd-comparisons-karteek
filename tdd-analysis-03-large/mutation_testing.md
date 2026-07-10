# Mutation Testing Analysis

Deep-dive gap analysis behind the [`README.md`](README.md#mutation-testing-results) summary table. `mutmut run` was executed against each codebase's package in an isolated per-project `.venv`, and every surviving mutant was inspected with `mutmut show <id>` and cross-referenced against the source and test files.

**Headline caveat, read this before the table:** the four codebases use two different architectural styles — one plain "god class" holding all state (T1), and three that split state into `@dataclass`-decorated value objects (`PointBatch`, `Customer`, etc.) with a `LoyaltyEngine` orchestrator on top (T2, NT1, NT2). `mutmut` 3.6.0 (the version installed here) **silently skips mutating every method inside any decorated class** — see `_skip_node_and_children` in `mutmut/mutation/file_mutation.py:236`:

```python
if isinstance(node, cst.ClassDef) and len(node.decorators):
    return True
```

`@dataclass` counts as a decorator, so this isn't a per-codebase bug — it's a tool limitation that happens to erase a different fraction of each codebase's domain logic depending on how much of that logic lives inside dataclass methods vs. the plain orchestrator class. The raw scores below are real and correctly computed from what `mutmut` actually generated, but **they are not scored on comparable surfaces**, and this fact overturns the naive reading of the ranking. Details in "Cross-cutting patterns" below.

## Ranking Table (as generated, before adjusting for the blind spot)

| Rank | ID | TDD used? | Codebase | Total Mutants | Killed | Survived | Mutation Score | Dataclass-method blind spot |
|---|---|---|---|---|---|---|---|---|
| 1 | NT1 | No | `sol-2026-07-09_15-23-32/` | 132 | 118 | 14 | **89.4%** | Severe — 6 methods, essentially all domain-calc logic |
| 2 | NT2 | No | `sol-2026-07-09_15-43-12/` | 130 | 113 | 17 | **86.9%** | Severe — 5 methods, essentially all domain-calc logic |
| 3 | T2 | Yes | `sol-2026-07-09_15-12-54/` | 139 | 119 | 20 | **85.6%** | Minor — 1 method (`PointBatch.is_expired`) |
| 4 | T1 | Yes | `sol-2026-07-09_14-59-45/` | 203 | 173 | 30 | **85.2%** | None — no dataclasses; full coverage |

Read this table with the blind-spot column in mind: **T1's 85.2% is the only fully-audited score of the four.** NT1 and NT2's scores are computed almost entirely over their thinner orchestration/CRUD layer, with their actual tier/balance/expiry math never exposed to a single mutation.

## Cross-Cutting Patterns

### 1. The `@dataclass`-method blind spot (tool limitation, not a codebase defect) — the dominant cross-cutting finding

Confirmed by diffing each codebase's `mutants/<pkg>/*.py` against its source: for every class carrying `@dataclass`, none of its user-defined methods appear as `x_ClassNameǁmethod__mutmut_N` trampolines — they're copied into the mutant tree byte-for-byte, unmutated.

| Codebase | Un-mutated methods | What they compute |
|---|---|---|
| NT1 (`loyalty/models.py`) | `PointBatch.is_expired:56`, `PointBatch.available:61`, `Customer._trailing_spend:91`, `Customer.tier:103`, `Customer.balance:107`, `Customer._is_signup_month:111` | Expiry check, spendable-balance calc, trailing-365-day spend sum, tier lookup, signup-month check — i.e. **the entire domain-rules layer** |
| NT2 (`loyalty/engine.py`) | `PointBatch._is_signup_month_batch:65`, `PointBatch.is_expired:71`, `Customer._trailing_spend:101`, `Customer.get_tier:116`, `Customer.get_balance:120` | Same set of domain rules; `LoyaltyEngine.get_tier:406`/`get_balance:386` are thin delegates that just call these (confirmed by reading their bodies — 3 lines each, existence-check + delegate) |
| T2 (`loyalty_engine/engine.py`) | `PointBatch.is_expired:17` only | Just the 90-day expiry check; `_trailing_spend`, `get_tier`, `get_balance` are `LoyaltyEngine` methods (plain class, lines 57/101/139) and *were* fully mutated |
| T1 (`loyalty/engine.py`) | none | No `@dataclass` anywhere; internal state is plain dicts inside one `LoyaltyEngine` class |

**Why this matters more than a footnote:** NT1's two independently-identified High-severity correctness bugs (see NT1 section below) both live inside methods on this un-mutated list (`PointBatch.is_expired`, and the batch-ordering assumption baked into how `Customer.batches` is consumed). Mutation testing, as configured here, was structurally incapable of surfacing them — not because the test suite is unusually strong there, but because no mutant was ever generated to test against. Conversely, NT2's clean bill of health on its own `_trailing_spend`/`get_tier`/`get_balance`/`is_expired` methods should be read as "unexamined," not "verified" — the 86.9% score simply never touched that code.

**Recommendation for any follow-up mutation-testing pass on this style of codebase**: either avoid `@dataclass` for classes with meaningful behavior (keep it for pure data, hand-write `__init__`/plain classes for anything with methods), or use a mutation tool/version that mutates decorated-class bodies, before trusting the resulting score as a completeness signal.

### 2. Dead / write-only fields echoed into records but never read back (equivalent mutants, all four codebases)

Every codebase stores identifying fields (`purchase_id`, `customer_id`) or duplicate accounting fields (`points_earned`, `original_points`/`earned`) on its purchase/batch records purely for potential introspection, then never reads them back anywhere in the engine:

- T1 `record_purchase__mutmut_6/7/8/9/17/18/39/40/41/42/53/54` (`loyalty/engine.py:52-80`) — `"id"`, `"customer_id"`, `"purchase_id"`, `"points"`, `"points_earned"` dict keys, all write-only.
- T2 `create_customer__mutmut_2`, `record_purchase__mutmut_10/21/32/36` (`loyalty_engine/engine.py:55,72,83,92,96`) — `Customer.customer_id`, `Customer.tier`, `PointBatch.earned`, `Purchase.purchase_id`, `Purchase.points_earned`.
- NT1 `record_purchase__mutmut_13/14/17/23/32/38`, `register_customer__mutmut_4` — `PurchaseRecord.purchase_id/customer_id/points_earned`, `PointBatch.original_points`, `Customer.customer_id`.
- NT2 `record_purchase__mutmut_30/34/46` (`loyalty/engine.py:246,249,258`) — `Purchase.purchase_id/points_earned`, `PointBatch.original_points`.

**Verdict**: genuinely equivalent mutants — every lookup goes through dict keys or separately-returned result objects, never through these stored fields. Not a test gap; a code-cleanliness note (delete the dead fields, or add one assertion per codebase if they're meant as a public audit trail).

### 3. Boundary values exercised near, but never exactly at, spec thresholds (real gaps, T1/T2/NT2 — NT1's equivalent logic is unreachable per Pattern 1)

The task spec (`task.md`) defines several hard cutoffs — tier thresholds ($1,000 / $5,000), the 365-day trailing window, the 90-day expiry window, and "spend more than balance should fail." All three fully-mutated-in-this-area codebases have tests that sit comfortably inside or outside these boundaries but never pin the exact edge:

- T1: `_compute_tier__mutmut_1/2` ($5,000 Gold threshold, `>=` vs `>`/`>=5001`), `_trailing_spend__mutmut_4/16` (365-day window edge), `spend_points__mutmut_6` (exact-full-balance spend).
- T2: `_trailing_spend__mutmut_4/10` (365-day window edge, `>` vs `>=`), `spend_points__mutmut_20` (partial spend after an expired-then-valid batch sequence — see "possible latent bug" note below), `spend_points__mutmut_23` (zero-amount spend contract undefined).
- NT2: `record_purchase__mutmut_15/18/20` (365-day window edge, duplicated inline in `record_purchase` rather than reusing `Customer._trailing_spend`), `spend_points__mutmut_24` (borderline: excluding a batch with exactly 1 remaining point).

**Verdict**: real gaps in every case — manual verification (by each subagent) confirmed the *current* code is correct at every one of these boundaries. But none of them is pinned, so a future refactor could silently regress any of them with no test failing. This is the single most actionable, consistent fix across the study: **add one exact-boundary test per threshold, per codebase.**

### 4. Error messages asserted only by loose substring match (real but low-value gap, all four)

Every codebase's tests use `pytest.raises(ValueError, match="some-substring")`, which still matches if the message is reordered, re-cased, or wrapped in marker characters. Representative survivors: T1 `record_refund__mutmut_4`, T2 `record_refund__mutmut_2`, NT1 `record_purchase__mutmut_8/9` + `spend_points__mutmut_6/7`, NT2 `record_purchase__mutmut_6/7` + `spend_points__mutmut_6/7`.

**Verdict**: real but intentionally low-priority — substring matching on error text is a defensible, common practice; tightening it to exact-string assertions is optional polish, not a correctness fix.

### 5. Equivalent mutants from a single-batch-per-purchase data model (T1, and structurally similar in others)

Where a purchase always produces exactly one points-batch (no design here allows splitting a purchase's points across >1 batch), any mutation to loop-accumulation vs. assignment (`+=` vs `=`), or `break` vs `continue` vs `return` in a loop that runs at most once, is unobservable. T1's Cluster E (`spend_points__mutmut_22/23/28`, `record_refund__mutmut_9`) is the clearest example. **Verdict**: equivalent under the current model, but flags a latent test-debt trap if the data model ever gains multi-batch purchases.

### 6. Defensive/unreachable guard code for "should never happen" invariants (NT1, NT2)

Both codebases have a runtime guard (NT1 `_get_batch`'s `RuntimeError` for a purchase with no matching batch; NT2 `record_refund`'s `next(..., None)` default) that's unreachable through the public API because `record_purchase` always creates exactly one batch atomically. **Verdict**: equivalent/dead defensive code, not a gap — arguably worth simplifying away rather than testing.

## Per-Codebase Sections (best to worst by raw mutation score)

### 1st (raw) — NT1 · No TDD · `sol-2026-07-09_15-23-32/` · 132 total, 118 killed, 14 survived · **89.4%**

**Read this score with Pattern 1 above front-of-mind: 131 of 132 mutants (99.2%) came from `engine.py`; `models.py` — home to the domain rules and both bugs below — produced exactly one mutant, on a module-level function.** This is the best score of the four and the worst human-rated correctness of the four; the mismatch is explained almost entirely by what mutmut couldn't see, not by test rigor.

**⚠️ Latent bugs (previously flagged by independent human review, now grounded in code):**
1. **`PointBatch.is_expired` mishandles `as_of` dates earlier than `earned_date`** (`loyalty/models.py:56-59`): `(as_of - self.earned_date).days >= EXPIRY_DAYS` goes negative and thus `False` (not expired) if queried before the points were earned — a backdated purchase or an out-of-order `as_of` query would wrongly count not-yet-earned points as spendable. Per task.md, points shouldn't be countable before they exist. **Unreachable by mutmut** (dataclass method).
2. **`spend_points` consumes `customer.batches` in list/insertion order, not purchase-date order** (`loyalty/engine.py:172-174`) — the code comment admits the assumption ("batches are appended in chronological order"); task.md rule 5 requires "oldest-dated purchase first" as a data property, independent of call order. A backdated purchase recorded after a later one is drawn down last, violating spec. This method *is* on the mutated surface, but no mutation operator perturbs "iterate over an unsorted list" — this bug class is structurally outside what statement-level mutation can catch; it needs an out-of-order-insertion test, which none of the 74 existing tests provide (every test inserts purchases in increasing date order).
3. Code smell (not a bug, but evidence of a half-finished edit): `Customer._trailing_spend` (`models.py:93,96`) computes `cutoff` twice — once via a leap-year-aware `.replace(year=...)` expression, then immediately overwrites it with a plain `timedelta(days=365)` cutoff. The first line is dead.

**Breakdown by function (survivors)**

| Function | File | Survivors |
|---|---|---|
| `record_purchase` | engine.py | 8 |
| `spend_points` | engine.py | 4 |
| `register_customer` | engine.py | 1 |
| `_get_batch` | engine.py | 1 |
| *(all of `models.py`'s domain logic)* | models.py | **0 generated** — see Pattern 1 |

**Clustered gaps** (all in the mutated `engine.py` surface — see Patterns 1/2/4/6 above for specifics and line citations): dead/write-only `PurchaseRecord`/`PointBatch`/`Customer` fields (Pattern 2), loose error-message matching (Pattern 4), equivalent off-by-one loop sentinels in `spend_points` (functionally unreachable given validated non-negative inputs), and an unreachable defensive `RuntimeError` in `_get_batch` (Pattern 6).

### 2nd (raw) — NT2 · No TDD · `sol-2026-07-09_15-43-12/` · 130 total, 113 killed, 17 survived · **86.9%**

Same blind spot as NT1 applies here (Pattern 1): `Customer._trailing_spend/get_tier/get_balance` and `PointBatch._is_signup_month_batch/is_expired` are all un-mutated dataclass methods containing the actual domain math; `LoyaltyEngine.get_tier:406`/`get_balance:386` are 3-line delegates that were mutated but don't add real coverage of the math itself. No confirmed bug was found here, but — per Pattern 1 — that's because this layer was never examined, either by the subagent's manual reading (which found it correct) *and* by mutmut (which never got the chance to probe it), not because mutation testing vindicated it.

**Breakdown by function (survivors, mutated surface only)**

| Function | Survivors |
|---|---|
| `record_purchase` | 8 |
| `spend_points` | 6 |
| `record_refund` | 3 |

**Clustered gaps**:
- **Real gap** — `record_purchase` re-implements the trailing-365-day filter inline (`engine.py:233-239`) instead of reusing `Customer._trailing_spend`, and no test pins its boundary when the *first* purchase should roll off before a *second* purchase (only `get_tier`/`get_balance` boundary cases are tested) — `record_purchase__mutmut_15/18/20`. Fix: a two-purchase test spanning the 365-day boundary between purchases, not just between a purchase and a query date.
- **Borderline real gap** — `spend_points__mutmut_24` (`engine.py:369`, `remaining_points > 0` → `> 1`) would wrongly skip a batch with exactly 1 remaining point in a multi-batch spend; untested because no test spends across a batch with exactly 1 point left. Fix: a 3-batch (1/100/100 points) spend test.
- **Equivalent/dead** — write-only `Purchase.purchase_id/points_earned`, `PointBatch.original_points` (Pattern 2); floor-at-zero arithmetic making `spend_points__mutmut_23/26/27` unobservable; unreachable `record_refund` "no matching batch" guard (Pattern 6).
- Loose error-message matching (Pattern 4) on both `record_purchase` and `spend_points` validation messages.

### 3rd (raw) — T2 · TDD · `sol-2026-07-09_15-12-54/` · 139 total, 119 killed, 20 survived · **85.6%**

Only a small slice of this codebase's domain logic (`PointBatch.is_expired:17`) sits behind the dataclass blind spot (Pattern 1) — `_trailing_spend`, `get_tier`, and `get_balance` are all `LoyaltyEngine` methods and were fully mutated. This is the most-completely-audited score after T1.

**⚠️ Possible latent-bug-shaped gap (code is correct today, but the invariant is unpinned):**
`spend_points`'s expired-batch skip (`engine.py:129-130`, `if batch.is_expired(as_of): continue`) survives a `continue`→`break` mutation. Manually verified: a customer with an expired 100-pt batch followed by a valid 100-pt batch, spending a *partial* 50 points, returns the wrong `remaining_balance` (100 instead of 50) under the mutant — but the only existing test on this path (`test_spend_skips_expired_batches`) spends the *entire* balance, so `break` and `continue` coincidentally produce the same final answer. Today's code is correct; the test suite doesn't actually pin why.

**Breakdown by function (survivors)**

| Function | Survivors |
|---|---|
| `spend_points` | 4 |
| `_trailing_spend` | 4 |
| `record_purchase` | 4 |
| `_tier_for_spend` | 3 |
| `record_refund` | 3 |
| `create_customer` | 1 |
| `get_tier` | 1 |

**Clustered gaps**: dead/write-only `Customer.tier`, `Purchase.purchase_id/points_earned`, `PointBatch.earned` fields and an unreachable `_tier_for_spend` fallback branch (Pattern 2); 365-day boundary untested for `>` vs `>=` and 365 vs. 366 days (Pattern 3); a genuine zero-amount `spend_points` contract gap (`mutmut_23`, `break`→`return` on `to_consume <= 0` returns `None` instead of a result dict — spec is silent on whether 0-point spends are valid, and the code has no explicit guard); loose error-message matching (Pattern 4); one thin real gap around 3+-purchase trailing-spend summation (`_trailing_spend__mutmut_11`, `+=` vs `=`) that existing multi-purchase tests should probably already kill — worth a second look with a dedicated 3-purchase regression test to be sure.

### 4th (raw) — T1 · TDD · `sol-2026-07-09_14-59-45/` · 203 total, 173 killed, 30 survived · **85.2%**

**The only fully-audited score in this study** — T1 has no `@dataclass` classes at all (state is plain dicts inside one `LoyaltyEngine` class), so every line of domain logic was exposed to mutation. Its raw score is the lowest of the four, but it's the most trustworthy number, and no latent bug was found — every survivor is either a dead/write-only field, an equivalent mutant, or a genuine-but-currently-harmless boundary/message gap.

**Breakdown by function (survivors)**

| Function | Survivors |
|---|---|
| `record_purchase` | 15 |
| `spend_points` | 5 |
| `_trailing_spend` | 4 |
| `_compute_tier` | 2 |
| `record_refund` | 2 |

**Clustered gaps**: dead/write-only dict keys (`"id"`, `"customer_id"`, `"purchase_id"`, `"points_earned"`) dominate `record_purchase`'s 15 survivors (Pattern 2); `uuid.uuid4()` auto-generated `purchase_id` is never checked when the caller omits one; the Gold-tier `$5,000` threshold and the 365-day window are both verified-correct-but-unpinned at their exact boundary (Pattern 3), as is spending exactly the full balance; loose error-message matching on the double-refund guard (Pattern 4); and a cluster of loop-control mutants in `spend_points`/`record_refund` that are equivalent today only because the data model never puts more than one batch per purchase (Pattern 5) — worth revisiting if that assumption ever changes.

## Overall Observations

- **The mutation-score ranking (NT1 > NT2 > T2 > T1) inverts the human-quality ranking from `comparison-report.md` (NT2 > T2 ≈ T1 > NT1) almost exactly at both ends.** NT1 has the best mutation score and the worst human-rated correctness (the only codebase with High-severity bugs); T1 has the worst mutation score and ties for 2nd-best human-rated correctness. Once the `@dataclass`-method blind spot (Pattern 1) is factored in, this stops looking like a paradox and starts looking like a measurement artifact: NT1's and NT2's scores were computed almost entirely over their thinner CRUD/orchestration layer, while their actual domain-rules layer (tier math, expiry math, balance math) was invisible to the tool — and that's precisely where NT1's two real bugs live. T1's score, by contrast, reflects its *entire* codebase, dead fields and all, which is why it looks "worse" while actually being the most honestly-measured.
- **Practical implication for the study**: raw mutation score should not be used, on its own, to rank these four codebases against each other, because they weren't scored on comparable surfaces. If mutation testing is to inform this kind of TDD-vs-non-TDD comparison going forward, either normalize for architecture (e.g. flatten dataclasses-with-methods into plain classes before running mutmut) or report mutation score per-file/per-class alongside a note on what fraction of the codebase was actually eligible for mutation — as this report now does.
- **No shipped, confirmed-wrong latent bug was found in T1, T2, or NT2** — every "possible latent bug" flagged for those three is a currently-correct-but-unpinned boundary or invariant (exact-balance spend, zero-amount spend, partial-spend-after-expired-batch, exact-365-day window), which is a genuine test-suite risk but not a live defect.
- **NT1 is the one codebase where mutation-adjacent analysis surfaced live, spec-violating defects** — both already known from the independent human review, but now traceable to exact lines (`loyalty/models.py:56-59` for the backdated-`as_of` expiry bug, `loyalty/engine.py:172-174` for the insertion-order-vs-date-order batch consumption bug) and confirmed to sit in code that this run of mutation testing structurally could not have caught regardless of test quality.
- **The most consistent, actionable, cross-codebase fix** is Pattern 3 (add one exact-boundary test per spec threshold, per codebase) — it's cheap, it's real, and it appears in every codebase whose domain logic was actually visible to the tool.
