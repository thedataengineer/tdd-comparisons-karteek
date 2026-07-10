# Comparison Report: Slot Code Validator Solutions

Four solutions to the same task (validate `{DAY}-{TIME}-{ROOM}-{CHECKSUM}` medical
scheduling slot codes) were evaluated independently. Each was assessed on **design
appropriateness**, **code quality**, and **test effectiveness**. All claims below were
verified by reading the source, running the tests, and probing edge cases directly —
not taken from the pre-existing per-folder analysis files.

## Overall Ranking

| Rank | Solution | Design | Code | Tests | Verdict |
|------|----------|:------:|:----:|:-----:|---------|
| 🥇 1 | **`sol-2026-07-09_11-55-41`** | 8 | 9 | 9 | Best overall — dataclass result, no bugs, 61 reason-asserting tests |
| 🥈 2 | **`sol-2026-07-09_11-59-54`** | 8 | 8 | 8 | Very close — dataclass result, but a Unicode-digit spec deviation |
| 🥉 3 | **`sol-2026-07-09_11-42-10`** | 7 | 8 | 7 | Correct & clean, but dict result + fewer tests + dead code |
| 4 | **`sol-2026-07-09_10-47-37`** | 6 | 7 | 7 | Weakest design (free-text error) + a genuine crash bug |

The field splits cleanly into two tiers:
- **Tier 1 (dataclass-based):** `11-55-41` and `11-59-54` model the result as a proper
  `ValidationResult` dataclass with a machine-readable `error_field` **and** a
  human-readable `error_reason`, backed by 58–61 tests.
- **Tier 2 (dict-based):** `11-42-10` and `10-47-37` return a bare dict where the failing
  rule is only encoded as free text, backed by ~20 tests.

All four pass their own suites at 100% line coverage, so coverage does **not**
discriminate between them — design and test *design* do.

---

## Dimension 1: Design (how the result is modeled)

The task's crux is *"return a structured result indicating whether the code is valid and,
if not, which specific rule failed and why."* This is where the solutions most differ.

- **`11-55-41` & `11-59-54` (best):** `ValidationResult` dataclass with
  `valid: bool`, `error_field: Optional[str]`, `error_reason: Optional[str]`. This
  separates the *which rule* (branchable) from the *why* (displayable) — the most faithful
  reading of the spec. Both use a clean linear pipeline of focused `_validate_*` helpers
  that short-circuits on first failure.
  - Shared nit: `error_field` is a bare string rather than an Enum, so callers must
    string-match constants. `11-59-54` additionally has **inconsistent casing** (lowercase
    `"format"` for structural errors vs uppercase `"DAY"/"TIME"/…`), a real wart for
    programmatic dispatch. Both carry a redundant custom `__repr__`.

- **`11-42-10`:** single `validate()` returning `{"valid": True}` or
  `{"valid": False, "reason": "<text>"}`. Clean and correct, but the failing rule is only
  discoverable by parsing the prose `reason` — no machine-readable field. Also defines
  `VALID_ROOM_PREFIXES` and never uses it (duplicated inside the regex).

- **`10-47-37` (weakest):** `validate()` returning `{"valid": True}` or
  `{"valid": False, "error": "<text>"}`. Same free-text limitation as above, and the
  success/failure shapes differ (no `error` key on success), forcing callers to guard.

**Design ranking:** `11-55-41` ≈ `11-59-54` > `11-42-10` > `10-47-37`.

---

## Dimension 2: Code Quality & Correctness

All four are readable and idiomatic. Correctness is where a real bug and a real deviation
appear:

- **`11-55-41` (9/10):** No bugs found across an extensive probe (TIME boundaries
  0800/1730, checksum modulo-to-zero, leading zeros, room digit counts, non-string input).
  Only a redundant/dead `hh > 23` message branch and parameter shadowing. Cleanest of the four.

- **`11-59-54` (8/10):** No ASCII-input bugs, **but a genuine spec deviation**: it uses
  `\d` + `int()`, which accept non-ASCII Unicode digits. So `MON-०८००-GP1-43` (Devanagari
  digits) *wrongly validates*. The spec clearly means ASCII `0-9` ("4-digit", "2-digit
  number"). Fix: `[0-9]` or `re.ASCII`. Also minor duplication re-extracting room digits in
  the checksum helper.

- **`11-42-10` (8/10):** No correctness bugs; all tricky cases (mod-100 wrap to `"00"`,
  boundaries, leading zeros) verified correct. Docked for dead/duplicated
  `VALID_ROOM_PREFIXES` and a slightly awkward ordering (computes checksum before validating
  checksum format).

- **`10-47-37` (7/10):** **Has an actual crash bug.** It guards numeric fields with
  `str.isdigit()` but converts with `int()`; these disagree on characters like superscript
  `²` (`"²".isdigit()` is `True`, `int("²")` raises). So `validate("MON-0800-GP1-²²")` throws
  an uncaught `ValueError` — a direct violation of the "always return a structured result"
  contract. Otherwise correct on all normal inputs.

**Correctness note:** the two dict solutions (`11-42-10`, `10-47-37`) use `.isdigit()`;
only `10-47-37`'s pattern actually crashes because `11-42-10`'s regex-first structure gates
the input differently. `11-59-54`'s issue is *acceptance* (too lenient), `10-47-37`'s is a
*crash* (worse — an unhandled exception). `11-55-41` avoids both.

**Code-quality ranking:** `11-55-41` > `11-42-10` ≈ `11-59-54` > `10-47-37`.

---

## Dimension 3: Test Effectiveness

The key quality signal here is whether invalid-case tests assert *which rule failed and
why*, rather than just `valid is False`. All four do this to some degree, but depth varies
enormously.

| Solution | Tests | Asserts failure *reason*? | Boundary coverage | Notable gaps |
|----------|:-----:|---------------------------|-------------------|--------------|
| `11-55-41` | **61** | Yes — `error_field` + reason substrings | Excellent (0800/1730/0730/1800, all days/prefixes, wrap) | checksum `"00"` correct-case unasserted; a couple duplicate tests; tests couple to private helpers |
| `11-59-54` | 58 | Yes — `error_field` + reason substrings | Excellent | **triple-duplicated** 1800 test; missing `%100==0` correct case; no Unicode/ASCII test (misses its own bug) |
| `11-42-10` | 21 | Partial — broad category substrings | Good | untested (but correct) edges: lowercase, empty, checksum `"00"`, 3-digit checksum/room |
| `10-47-37` | 20 | Yes — category substrings | Good | **no non-numeric TIME/CHECKSUM test** — the exact gap hiding its crash bug; analysis file wrongly claims this path is covered |

- **`11-55-41` (9/10)** and **`11-59-54` (8/10)** have genuinely mutation-resistant suites:
  ~3× the test count, boundary-focused, and asserting the specific failing field. `11-55-41`
  edges ahead on breadth and fewer redundancies; `11-59-54` loses a point for three identical
  1800 tests and for not catching its own Unicode leniency.
- **`10-47-37` (7/10)** and **`11-42-10` (7/10)** are respectable for their size and *do*
  assert reasons, but both leave correct-but-untested edges. Critically, `10-47-37`'s suite
  has no non-numeric-checksum/TIME case — precisely the blind spot that lets its
  `ValueError` crash through — and its companion analysis file *overstates* coverage there.

**Test ranking:** `11-55-41` > `11-59-54` > `11-42-10` ≈ `10-47-37`.

---

## Agreement with the pre-existing analysis files

- `11-55-41` & `11-59-54`: their analysis files are **accurate**; I concur.
- `11-42-10`: summary claims "100% line and branch coverage" — line coverage is genuinely
  100%, but branch coverage was not actually measured in the run. Minor overstatement.
- `10-47-37`: its analysis file **incorrectly** claims the non-numeric-checksum path is
  covered. It is not — that branch is only hit via the length half of an `or`, and the gap
  hides a real crash bug.

---

## Bottom Line

**Winner: `sol-2026-07-09_11-55-41`.** It makes the best design choice (dataclass result
separating machine-readable field from human-readable reason), has the cleanest and
bug-free implementation, and is backed by the strongest test suite (61 tests that assert
*why* validation failed, with thorough boundary coverage).

**`sol-2026-07-09_11-59-54`** is a very close second with the same strong design, held back
only by a minor Unicode-digit leniency and some redundant tests.

The two **dict-returning** solutions rank lower primarily on design — encoding "which rule
failed" as free text rather than a structured field is a weaker fit for the spec — and on
thinner test suites. **`10-47-37`** places last because it additionally carries a genuine
crash bug that its own tests and analysis missed.

### One clear pattern
The dataclass solutions (`11-55-41`, `11-59-54`) came with ~3× as many tests (58–61 vs
20–21). The extra tests didn't just pad coverage — they drove a more disciplined,
machine-consumable result design and caught more edge behavior. Test depth and design
quality moved together.
