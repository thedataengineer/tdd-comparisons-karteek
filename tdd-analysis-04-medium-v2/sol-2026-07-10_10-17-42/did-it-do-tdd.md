## 2. TDD Process Analysis

### Did the agent follow TDD?

**Overall: Yes, with very high fidelity.** The TDD loop was followed throughout the session.

**Positive evidence:**
- For each new module (parse, aggregate, format, validate, pipeline), the first test was written *before any implementation*, causing an **import error / collection error** (the canonical "red" in TDD when there's no module yet). This is the clearest signal that tests preceded implementation.
- Tests were added one at a time throughout the session (25+ named `TEST N –` checkpoints in the conversation).
- Every test failure was confirmed before writing implementation; every implementation was confirmed to pass before moving to the next test.
- The agent used the spec instruction "Design the CONTRACT up front" to justify writing `models.py` before any tests — this is a borderline case but well-reasoned and consistent with the instruction.
- The final coverage check showed 100% line and branch coverage.

**One test modification:**
- `test_format_headcount_is_plain_integer` was adjusted. The original version asserted `"$42" not in result` for the *entire* table output, but the agent realized (correctly) that the TOTAL row formats all values with `$` regardless of category. The test was narrowed to check only the HEADCOUNT *row*, not the entire table. This was a **legitimate correction** — the original assertion was contradicting a valid spec interpretation, not weakening a meaningful constraint. The agent explicitly explained the rationale before changing the test.

**Adherence score: ~95%** — essentially full adherence.

