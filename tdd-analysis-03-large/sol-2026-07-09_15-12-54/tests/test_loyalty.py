from datetime import date
import pytest
from loyalty_engine import LoyaltyEngine


# ── Test 1: Creating a customer ──────────────────────────────────────────────
def test_create_customer():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 15))
    # A freshly created customer should exist and have Bronze tier
    tier = engine.get_tier("c1", as_of=date(2024, 1, 15))
    assert tier == "Bronze"


# ── Test 2: Purchase earns points at Bronze rate ──────────────────────────────
def test_purchase_earns_points_bronze():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 1))
    result = engine.record_purchase("c1", purchase_id="p1", amount=100.0, purchase_date=date(2024, 2, 1))
    assert result["points_earned"] == 100
    assert result["tier"] == "Bronze"


# ── Test 3: Tier upgrade to Silver on the triggering purchase ───────────────
def test_tier_upgrades_to_silver_on_triggering_purchase():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 1))
    # First purchase: $900 -> still Bronze
    engine.record_purchase("c1", "p1", 900.0, date(2024, 2, 1))
    # Second purchase: $100 -> total $1000 -> Silver; points earned at Silver rate
    result = engine.record_purchase("c1", "p2", 100.0, date(2024, 2, 2))
    assert result["tier"] == "Silver"
    assert result["points_earned"] == 125  # int(100 * 1.25)


# ── Test 4: Gold rate applied when spend hits $5000 ────────────────────
def test_tier_upgrades_to_gold():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 1))
    engine.record_purchase("c1", "p1", 4900.0, date(2024, 2, 1))
    # This $100 purchase pushes total to $5000 -> Gold
    result = engine.record_purchase("c1", "p2", 100.0, date(2024, 2, 2))
    assert result["tier"] == "Gold"
    assert result["points_earned"] == 150  # int(100 * 1.5)


# ── Test 5: Points are floored (Silver rate on non-round amount) ───────────
def test_points_are_floored():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 1))
    # Push into Silver first
    engine.record_purchase("c1", "p1", 1000.0, date(2024, 2, 1))
    # $10.40 at 1.25 = 13.0, int(...) = 13
    result = engine.record_purchase("c1", "p2", 10.40, date(2024, 2, 2))
    assert result["points_earned"] == 13


# ── Test 6: get_balance returns sum of non-expired batches ─────────────────
def test_get_balance():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 1))
    engine.record_purchase("c1", "p1", 200.0, date(2024, 2, 1))
    engine.record_purchase("c1", "p2", 300.0, date(2024, 2, 1))
    balance = engine.get_balance("c1", as_of=date(2024, 2, 1))
    assert balance == 500


# ── Test 7: Points expire after 90 days ───────────────────────────────
def test_points_expire_after_90_days():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 1))
    engine.record_purchase("c1", "p1", 100.0, date(2024, 2, 1))
    # 91 days later, points should be expired
    balance = engine.get_balance("c1", as_of=date(2024, 5, 2))  # Feb 1 + 91 days
    assert balance == 0


# ── Test 8: Points at exactly 90 days are still valid (boundary) ───────────
def test_points_valid_at_exactly_90_days():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 1))
    engine.record_purchase("c1", "p1", 100.0, date(2024, 2, 1))
    # exactly 90 days later
    balance = engine.get_balance("c1", as_of=date(2024, 5, 1))  # Feb 1 + 90 days
    assert balance == 100


# ── Test 9: Signup-month points never expire ───────────────────────────
def test_signup_month_points_never_expire():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 15))
    # Purchase in signup month (January 2024)
    engine.record_purchase("c1", "p1", 100.0, date(2024, 1, 20))
    # Check well after 90 days
    balance = engine.get_balance("c1", as_of=date(2025, 1, 20))
    assert balance == 100


# ── Test 10: Spending points succeeds and reduces balance ──────────────────
def test_spend_points_success():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 1))
    engine.record_purchase("c1", "p1", 200.0, date(2024, 2, 1))
    result = engine.spend_points("c1", 50, as_of=date(2024, 2, 10))
    assert result["success"] is True
    assert result["remaining_balance"] == 150


# ── Test 11: Spending more than balance fails ───────────────────────────
def test_spend_points_insufficient_balance():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 1))
    engine.record_purchase("c1", "p1", 100.0, date(2024, 2, 1))
    result = engine.spend_points("c1", 200, as_of=date(2024, 2, 10))
    assert result["success"] is False
    assert result["remaining_balance"] == 100  # balance unchanged


# ── Test 12: Spending consumes oldest batch first ────────────────────────
def test_spend_consumes_oldest_first():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 1))
    engine.record_purchase("c1", "p1", 100.0, date(2024, 2, 1))   # 100 pts
    engine.record_purchase("c1", "p2", 200.0, date(2024, 2, 10))  # 200 pts
    # Spend 150: should drain all 100 from p1, then 50 from p2
    engine.spend_points("c1", 150, as_of=date(2024, 2, 20))
    # p1 batch should be empty; p2 should have 150 left
    customer = engine._customers["c1"]
    batches_by_date = sorted(customer.batches, key=lambda b: b.earned_date)
    assert batches_by_date[0].remaining == 0   # p1 drained
    assert batches_by_date[1].remaining == 150  # p2 partially drained


# ── Test 13: Expired batches are skipped during spending ──────────────────
def test_spend_skips_expired_batches():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 1))
    engine.record_purchase("c1", "p1", 100.0, date(2024, 2, 1))   # will expire
    engine.record_purchase("c1", "p2", 200.0, date(2024, 5, 15))  # still valid
    # p1 is 91+ days before Aug 1 spend date (Feb 1 + 91 = May 2); May 15 is 77 days before Aug 1 -> valid
    spend_date = date(2024, 8, 1)
    balance = engine.get_balance("c1", as_of=spend_date)
    assert balance == 200  # p1 expired, only p2 counts
    result = engine.spend_points("c1", 200, as_of=spend_date)
    assert result["success"] is True


# ── Test 14: Refund claws back all points if none spent ───────────────────
def test_refund_claws_back_points():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 1))
    engine.record_purchase("c1", "p1", 200.0, date(2024, 2, 1))
    result = engine.record_refund("p1", refund_date=date(2024, 2, 10))
    assert result["points_clawed_back"] == 200
    balance = engine.get_balance("c1", as_of=date(2024, 2, 10))
    assert balance == 0


# ── Test 15: Refund only claws back remaining (unspent) points ─────────────
def test_refund_partial_clawback_after_spend():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 1))
    engine.record_purchase("c1", "p1", 200.0, date(2024, 2, 1))  # 200 pts
    # Spend 80 points from p1 batch
    engine.spend_points("c1", 80, as_of=date(2024, 2, 5))
    # Refund p1: only 120 remaining points can be clawed back
    result = engine.record_refund("p1", refund_date=date(2024, 2, 10))
    assert result["points_clawed_back"] == 120
    assert engine.get_balance("c1", as_of=date(2024, 2, 10)) == 0


# ── Test 16: Refunding a purchase twice raises an error ───────────────────
def test_double_refund_raises():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 1))
    engine.record_purchase("c1", "p1", 100.0, date(2024, 2, 1))
    engine.record_refund("p1", refund_date=date(2024, 2, 10))
    with pytest.raises(ValueError):
        engine.record_refund("p1", refund_date=date(2024, 2, 15))


# ── Test 17: get_tier reflects trailing spend (refunds can downgrade tier) ───
def test_tier_downgrade_after_refund():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 1))
    engine.record_purchase("c1", "p1", 1000.0, date(2024, 2, 1))  # -> Silver
    assert engine.get_tier("c1", as_of=date(2024, 2, 2)) == "Silver"
    engine.record_refund("p1", refund_date=date(2024, 2, 5))
    # After refund spend drops to $0, so Bronze
    assert engine.get_tier("c1", as_of=date(2024, 2, 5)) == "Bronze"


# ── Test 18: Purchases older than 365 days excluded from tier calc ────────
def test_trailing_365_days_tier_calculation():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2023, 1, 1))
    # Old purchase (366 days before check date)
    engine.record_purchase("c1", "p1", 5000.0, date(2023, 1, 1))
    # check_date = Jan 2, 2024; cutoff = Jan 2, 2023; p1 on Jan 1 2023 is exactly 366 days before
    # _trailing_spend uses > cutoff (strictly after), so Jan 1 is NOT included
    tier = engine.get_tier("c1", as_of=date(2024, 1, 2))
    assert tier == "Bronze"


# ── Test 19: Purchase within 365-day window still counts ──────────────────
def test_trailing_365_purchase_within_window_counts():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2023, 1, 1))
    # 364 days before check date -> within window
    engine.record_purchase("c1", "p1", 5000.0, date(2023, 1, 3))
    tier = engine.get_tier("c1", as_of=date(2024, 1, 2))
    assert tier == "Gold"


# ── Test 20: Refund doesn't touch other batches; no negative balance ────────
def test_refund_does_not_touch_other_batches():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 1))
    engine.record_purchase("c1", "p1", 100.0, date(2024, 2, 1))  # 100 pts
    engine.record_purchase("c1", "p2", 50.0, date(2024, 2, 5))   # 50 pts
    # Spend all 150
    engine.spend_points("c1", 150, as_of=date(2024, 2, 10))
    # Refund p1 - batch is already 0, so claws back 0 (no negative)
    result = engine.record_refund("p1", refund_date=date(2024, 2, 12))
    assert result["points_clawed_back"] == 0
    assert engine.get_balance("c1", as_of=date(2024, 2, 12)) == 0


# ── Test 21: Signup-month points are spendable long after 90 days ──────────
def test_signup_month_points_spendable_after_90_days():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 3, 1))
    engine.record_purchase("c1", "p1", 100.0, date(2024, 3, 10))  # signup month
    # 200 days later, should still be spendable
    result = engine.spend_points("c1", 100, as_of=date(2024, 9, 26))
    assert result["success"] is True
    assert result["remaining_balance"] == 0


# ── Test 22: Spend stops early when to_consume reaches zero (multiple batches) ──
def test_spend_stops_early_when_consumed():
    engine = LoyaltyEngine()
    engine.create_customer("c1", signup_date=date(2024, 1, 1))
    engine.record_purchase("c1", "p1", 100.0, date(2024, 2, 1))  # 100 pts
    engine.record_purchase("c1", "p2", 100.0, date(2024, 2, 2))  # 100 pts
    engine.record_purchase("c1", "p3", 100.0, date(2024, 2, 3))  # 100 pts
    # Spend exactly 100: drains p1, then to_consume==0 -> break, p2 & p3 untouched
    engine.spend_points("c1", 100, as_of=date(2024, 2, 10))
    assert engine.get_balance("c1", as_of=date(2024, 2, 10)) == 200
