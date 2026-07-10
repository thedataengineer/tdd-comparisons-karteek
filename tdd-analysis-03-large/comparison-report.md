# Loyalty Points Engine — Comparative Analysis of Four Solutions

Four independent solutions to the same `task.md` (an in-memory loyalty-points
library) were analyzed. Each was read against the spec, its tests were executed,
and its pre-existing self-analysis was independently verified. Below, solutions
are labelled **A–D** by timestamp:

| Label | Folder | Package | Tests | Coverage | Core bugs found |
|-------|--------|---------|-------|----------|-----------------|
| **A** | `sol-2026-07-09_14-59-45` | `loyalty/` (1 module) | 21 pass | 99% | none |
| **B** | `sol-2026-07-09_15-12-54` | `loyalty_engine/` (1 module, dataclasses) | 22 pass | 99% | none (core) |
| **C** | `sol-2026-07-09_15-23-32` | `loyalty/` + `models.py` | 74 pass | 99% | **2 High** |
| **D** | `sol-2026-07-09_15-43-12` | `loyalty/` (1 module, dataclasses) | 69 pass | 100% | none (core) |

All four suites pass and all report ~99–100% line coverage. **Coverage did not
predict correctness** — the solution with the most tests and highest test-count
(C, 74 tests) contains the only two High-severity bugs, while the smallest suite
(A, 21 tests) has no functional bugs. This is the central finding of the review.

---

## Final Ranking

### 🥇 1st — D (`sol-2026-07-09_15-43-12`)
**Scores: Design 8 · Code 9 · Tests 8 · Correctness 8 — avg 8.25**

The best-engineered solution. A single well-documented module with a
`LoyaltyEngine` facade, `Tier` enum, and clean `Customer`/`Purchase`/`PointBatch`
dataclasses. It is the **only solution with real input validation** (unknown
customer, non-positive amounts, duplicate purchase IDs, duplicate registration,
double refund), the **only one at 100% line coverage**, and its 69 tests are
precise and behavior-driven with strong boundary coverage ($999.99/$1000,
90/91-day, 365/366-day, signup first/last day). No core rule is implemented
incorrectly.

Remaining issues are all Low-severity edge cases: out-of-chronological-order
purchase recording double-counts future spend toward tier (`engine.py:233-239`,
because `record_purchase` bounds the window on one side while `_trailing_spend`
bounds both); refunds report clawing back already-expired points; and
`spend_points`' eligibility filter diverges from `get_balance`'s (latent, not
currently exploitable). Minor dead fields (`points_earned`, `original_points`)
and an unused `refund_date` parameter.

### 🥈 2nd — B (`sol-2026-07-09_15-12-54`)
**Scores: Design 7 · Code 7 · Tests 8 · Correctness 8 — avg 7.5**

A clean, idiomatic dataclass-based single module (`PointBatch`/`Purchase`/
`Customer` + `LoyaltyEngine` facade). All core domain rules verified correct,
with strong, meaningful test assertions and good boundary coverage (both the
90/91-day and 365-day edges). Ranks above A on the strength of a proper typed
data model and marginally better tests.

Weaknesses: untyped `dict` return values, dead state (`Customer.total_spend_trailing`
is never read; `Customer.tier` is written but `get_tier` recomputes), essentially
no error handling (bare `KeyError`), and a real-but-caller-dependent duplicate-
`purchase_id` bug (a re-used ID appends a second batch but refund only zeroes the
first). Its trailing-365 window is exclusive at the far boundary — an
interpretation choice its own tests bake in.

### 🥉 3rd — A (`sol-2026-07-09_14-59-45`)
**Scores: Design 7 · Code 7 · Tests 7 · Correctness 9 — avg 7.5**

The most minimal solution and, notably, the **most functionally correct** — no
bugs survived rigorous edge probing (float-floor, exact tier boundaries, signup
same-month-different-year, drained-batch clawback all handled). Tied with B on
average but ranked third because its design is weaker: state is untyped nested
dicts, and it carries a **vestigial `points_batches` list** that is always
single-element — dead generality that misleads. Fewest tests (21), a few of
which reach into internal structure (white-box coupling), and several subtle
edges untested (exact tier boundaries, signup same-month-different-year,
spend-atomicity-on-failure). Shares the silent `purchase_id`-overwrite and
missing-validation gaps.

*A vs B is close.* Both are correct single-module facades; B wins on a typed
data model and slightly stronger tests, A wins on a hair more correctness. B is
placed second as the better-designed, more maintainable artifact.

### 4th — C (`sol-2026-07-09_15-23-32`)
**Scores: Design 8 · Code 7 · Tests 6 · Correctness 6 — avg 6.75**

Paradoxically the most *ambitious* solution — cleanest package split
(`models.py` + `engine.py`), explicit result dataclasses
(`PurchaseResult`/`RefundResult`/`SpendResult`), and by far the most tests (74).
Its **design scores highest of all four**. But it ranks last because it is the
only solution with High-severity functional bugs, and its large suite fails to
catch them:

1. **[HIGH] Oldest-batch-first uses insertion order, not purchase date**
   (`engine.py:174`). A backdated purchase recorded after a later one is drawn
   down in the wrong order.
2. **[HIGH] Balance/spend count future-dated batches** (`models.py:56-59`).
   `is_expired` returns negative day-deltas as "not expired," so
   `get_balance`/`spend_points` include and allow spending points from purchases
   dated after the query date.

Both bugs are invisible to the suite because **every test records purchases in
chronological order and never queries "as of" a date before a purchase** — the
tests confirm the implementation's own assumptions rather than adversarially
probing the spec. Also carries dead/overwritten code in `_trailing_spend`
(`models.py:93`) and a low-severity expired-batch clawback reporting inaccuracy.

---

## Scoreboard

| Criterion | A | B | C | D |
|-----------|---|---|---|---|
| Design | 7 | 7 | **8** | **8** |
| Code Quality | 7 | 7 | 7 | **9** |
| Test Effectiveness | 7 | 8 | 6 | 8 |
| Correctness | **9** | 8 | 6 | 8 |
| **Average** | 7.5 | 7.5 | 6.75 | **8.25** |
| **Rank** | 3 | 2 | 4 | **1** |

---

## Cross-cutting observations

- **Test count ≠ test quality.** C (74) and D (69) dwarf A (21) and B (22), yet
  C is the buggiest and A is the cleanest on correctness. What separated D from C
  was not volume but whether tests *adversarially probe the spec* (out-of-order
  input, future-dated queries, expired refunds) vs *mirror the happy path*.
- **The recurring latent bug across three solutions** (B, C, D) is
  **out-of-chronological-order purchase recording** — none enforce or test that
  batches are sorted by purchase date. In C it's an active High bug; in B/D it's
  a Low/latent issue. The spec never guarantees ordered input, so this is a
  genuine shared blind spot.
- **Two shared spec-ambiguity choices:** (1) the trailing-365 boundary
  (inclusive vs exclusive at exactly 365 days) is handled differently and each
  suite bakes its own choice in; (2) whether a refund should report clawing back
  *already-expired* points — B/C/D all report the full remaining count regardless
  of expiration. These are defensible readings, not clear defects.
- **Data modelling:** B, C, and D use dataclasses/enums (good); A uses untyped
  nested dicts with a vestigial list (weakest model). Only D validates inputs.
- **Every self-analysis was over-optimistic.** All four pre-existing reports
  treated high coverage as near-proof of correctness and missed real bugs — most
  significantly C's, whose summary called its suite "comprehensive" while two
  High bugs sat uncaught.

## Recommendation

**D is the solution to ship.** It combines the best code quality, the only real
input validation, full coverage, and no core bugs. Before use, address its three
Low-severity edges — most importantly unify the tier-window bounds between
`record_purchase` and `_trailing_spend` and add tests for out-of-order and
future-dated input, the blind spot shared across the field.
