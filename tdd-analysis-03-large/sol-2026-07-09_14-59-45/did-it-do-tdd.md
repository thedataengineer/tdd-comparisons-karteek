## 3. TDD Process Adherence

The agent followed the TDD loop very faithfully:

| Step | Evidence |
|------|----------|
| Write one test first | MSG 7: wrote only `test_create_customer` initially |
| Run and see it fail | MSG 10: `ImportError` (implementation doesn't exist yet) ✅ |
| Write minimal impl | MSG 11: created `engine.py` with stub `create_customer` and `get_tier` |
| All tests green | MSG 14: `1 passed` ✅ |
| Repeat for each behavior | Pattern holds for all 21 tests |

Each subsequent test was added one at a time (via `edit` appending, then `cat >>` appending), run first to confirm red, then implementation updated to go green.

**No test was weakened**: Edits to `test_loyalty.py` were exclusively additions, never modifications of existing assertions.

**Minor glitch**: At MSG 39 and MSG 41, the agent attempted to add `test_get_balance_returns_total_unspent_points` twice using the `edit` tool (duplicate attempts with slightly different whitespace). The second attempt also failed silently. At MSG 43, the agent used `tail` to verify the file state and then at MSG 45 correctly used `cat >>` to append the test. This was a temporary tool-usage confusion, not a TDD violation.

**Coverage**: The agent ran `--cov` twice (MSG 121 at 20 tests, MSG 129 at 21 tests), found 99% coverage, and confirmed by running the full verbose suite at MSG 131.
