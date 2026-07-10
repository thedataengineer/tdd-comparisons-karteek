## 2. TDD Process Analysis

### Red–Green–Refactor Pattern

The agent ran tests frequently (28 pytest invocations for 22 tests), but the strict TDD loop was only followed for the **3 new method introductions**:

| Test | Red Phase | Cause of Failure | Then Green |
|------|-----------|-----------------|-----------|
| Test 1: `test_create_customer` | ✅ FAIL | `ImportError` — module didn't exist | ✅ PASS after implementation |
| Test 2: `test_purchase_earns_points_bronze` | ✅ FAIL | `AttributeError: 'LoyaltyEngine' has no 'record_purchase'` | ✅ PASS after implementation |
| Test 10: `test_spend_points_success` | ✅ FAIL | `AttributeError: 'LoyaltyEngine' has no 'spend_points'` | ✅ PASS after implementation |
| Test 14: `test_refund_claws_back_points` | ✅ FAIL | `AttributeError: 'LoyaltyEngine' has no 'record_refund'` | ✅ PASS after implementation |
| **Tests 3–9, 11–13, 15–22** | ❌ PASS immediately | Already implemented by previous broad impl | Not applicable |

**Root cause of violations:** When the agent implemented `record_purchase` (for test 2), it wrote a comprehensive implementation covering tier calculation, rates, expiry flags, and `get_balance`. This meant tests 3–9 passed immediately without a "red" phase. Similarly, `spend_points` and `record_refund` were implemented broadly, causing tests 11–13 and 15–22 to pass immediately.

Per TDD Rule 2: *"If it doesn't fail, the test isn't testing anything new — revise it."* The agent never revised tests that passed immediately; it simply moved on.

**This is a significant TDD process violation**: 18 out of 22 tests (82%) never had a proper "red" phase. The agent wrote `minimum implementation` only in the narrow sense that it didn't add unrelated code, but it pre-emptively implemented multiple features at once.

### Test Modifications

The only test change that resembled an adaptation was in test 7 (MSG 47), where:
- Before: `assert balance` (truthy check)  
- After: `assert balance == 0`

This was actually a **strengthening** of the assertion (made it more specific), not a weakening to accommodate implementation. It was caught before running the test. No tests were weakened or deleted.
