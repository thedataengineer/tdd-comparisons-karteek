"""
Comprehensive tests for the loyalty points engine.
Covers all domain rules: tiers, earning, expiration, refunds, spending.
"""

import pytest
from datetime import date, timedelta

from loyalty.engine import LoyaltyEngine, Tier, PointBatch, _tier_for_spend


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_engine_with_customer(
    customer_id: str = "alice",
    signup_date: date = date(2024, 1, 10),
) -> LoyaltyEngine:
    engine = LoyaltyEngine()
    engine.register_customer(customer_id, signup_date)
    return engine


# ===========================================================================
# 1. Tier calculation helper
# ===========================================================================

class TestTierForSpend:
    def test_zero_is_bronze(self):
        assert _tier_for_spend(0) == Tier.BRONZE

    def test_just_below_silver(self):
        assert _tier_for_spend(999.99) == Tier.BRONZE

    def test_silver_boundary(self):
        assert _tier_for_spend(1_000.00) == Tier.SILVER

    def test_mid_silver(self):
        assert _tier_for_spend(2_500.00) == Tier.SILVER

    def test_just_below_gold(self):
        assert _tier_for_spend(4_999.99) == Tier.SILVER

    def test_gold_boundary(self):
        assert _tier_for_spend(5_000.00) == Tier.GOLD

    def test_well_above_gold(self):
        assert _tier_for_spend(100_000) == Tier.GOLD


# ===========================================================================
# 2. Customer registration
# ===========================================================================

class TestRegistration:
    def test_register_returns_customer(self):
        engine = LoyaltyEngine()
        c = engine.register_customer("bob", date(2024, 6, 1))
        assert c.customer_id == "bob"
        assert c.signup_date == date(2024, 6, 1)

    def test_duplicate_registration_raises(self):
        engine = LoyaltyEngine()
        engine.register_customer("bob", date(2024, 6, 1))
        with pytest.raises(ValueError, match="already exists"):
            engine.register_customer("bob", date(2024, 6, 1))

    def test_unknown_customer_get_balance_raises(self):
        engine = LoyaltyEngine()
        with pytest.raises(ValueError, match="not found"):
            engine.get_balance("nobody", date(2024, 1, 1))

    def test_unknown_customer_get_tier_raises(self):
        engine = LoyaltyEngine()
        with pytest.raises(ValueError, match="not found"):
            engine.get_tier("nobody", date(2024, 1, 1))

    def test_unknown_customer_spend_raises(self):
        engine = LoyaltyEngine()
        with pytest.raises(ValueError, match="not found"):
            engine.spend_points("nobody", 10, date(2024, 1, 1))

    def test_unknown_customer_purchase_raises(self):
        engine = LoyaltyEngine()
        with pytest.raises(ValueError, match="not found"):
            engine.record_purchase("nobody", 100, date(2024, 1, 1), "p1")


# ===========================================================================
# 3. Earning points – basic rates
# ===========================================================================

class TestEarningPoints:
    def test_bronze_rate(self):
        engine = make_engine_with_customer()
        points, tier = engine.record_purchase("alice", 100, date(2024, 3, 1), "p1")
        assert tier == Tier.BRONZE
        assert points == 100   # 100 * 1.0

    def test_silver_rate(self):
        engine = make_engine_with_customer()
        # First push spend to Silver threshold, then buy more
        engine.record_purchase("alice", 1_000, date(2024, 3, 1), "p1")
        points, tier = engine.record_purchase("alice", 200, date(2024, 3, 2), "p2")
        assert tier == Tier.SILVER
        assert points == 250   # 200 * 1.25

    def test_gold_rate(self):
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 5_000, date(2024, 3, 1), "p1")
        points, tier = engine.record_purchase("alice", 100, date(2024, 3, 2), "p2")
        assert tier == Tier.GOLD
        assert points == 150   # 100 * 1.50

    def test_points_are_floored(self):
        engine = make_engine_with_customer()
        # Bronze: 99 * 1.0 = 99.0 -> 99 (exact)
        points, _ = engine.record_purchase("alice", 99, date(2024, 3, 1), "p1")
        assert points == 99

    def test_silver_fractional_floor(self):
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 1_000, date(2024, 3, 1), "p1")
        # 1 * 1.25 = 1.25 -> floor = 1
        points, tier = engine.record_purchase("alice", 1, date(2024, 3, 2), "p2")
        assert tier == Tier.SILVER
        assert points == 1

    def test_gold_fractional_floor(self):
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 5_000, date(2024, 3, 1), "p1")
        # 1 * 1.50 = 1.5 -> floor = 1
        points, tier = engine.record_purchase("alice", 1, date(2024, 3, 2), "p2")
        assert tier == Tier.GOLD
        assert points == 1

    def test_tier_upgrade_on_same_purchase(self):
        """A purchase that tips spend from Bronze to Silver earns at Silver rate."""
        engine = make_engine_with_customer()
        # Prior spend = $900 (Bronze).  This $200 purchase takes trailing to $1100 -> Silver.
        engine.record_purchase("alice", 900, date(2024, 3, 1), "p0")
        points, tier = engine.record_purchase("alice", 200, date(2024, 3, 2), "p1")
        assert tier == Tier.SILVER
        assert points == 250   # 200 * 1.25

    def test_tier_upgrade_to_gold_on_same_purchase(self):
        """A single large purchase can jump directly to Gold tier."""
        engine = make_engine_with_customer()
        points, tier = engine.record_purchase("alice", 5_000, date(2024, 3, 1), "p1")
        assert tier == Tier.GOLD
        assert points == 7_500  # 5000 * 1.50

    def test_duplicate_purchase_id_raises(self):
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 100, date(2024, 3, 1), "p1")
        with pytest.raises(ValueError, match="already exists"):
            engine.record_purchase("alice", 50, date(2024, 3, 2), "p1")

    def test_non_positive_amount_raises(self):
        engine = make_engine_with_customer()
        with pytest.raises(ValueError, match="positive"):
            engine.record_purchase("alice", 0, date(2024, 3, 1), "p1")
        with pytest.raises(ValueError, match="positive"):
            engine.record_purchase("alice", -10, date(2024, 3, 1), "p2")


# ===========================================================================
# 4. Tier queries (get_tier)
# ===========================================================================

class TestGetTier:
    def test_new_customer_is_bronze(self):
        engine = make_engine_with_customer()
        assert engine.get_tier("alice", date(2024, 3, 1)) == Tier.BRONZE

    def test_tier_after_purchases(self):
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 1_500, date(2024, 3, 1), "p1")
        assert engine.get_tier("alice", date(2024, 3, 2)) == Tier.SILVER

    def test_old_purchases_excluded_from_tier(self):
        """Purchases older than 365 days should not count toward tier."""
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 4_000, date(2023, 1, 1), "p1")
        # 366 days later the $4000 is outside the window
        as_of = date(2023, 1, 1) + timedelta(days=366)
        assert engine.get_tier("alice", as_of) == Tier.BRONZE

    def test_refunded_purchase_excluded_from_tier(self):
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 2_000, date(2024, 3, 1), "p1")
        assert engine.get_tier("alice", date(2024, 3, 2)) == Tier.SILVER
        engine.record_refund("p1", date(2024, 3, 5))
        assert engine.get_tier("alice", date(2024, 3, 6)) == Tier.BRONZE

    def test_tier_boundary_exact_1000(self):
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 1_000, date(2024, 3, 1), "p1")
        assert engine.get_tier("alice", date(2024, 3, 1)) == Tier.SILVER

    def test_tier_boundary_exact_5000(self):
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 5_000, date(2024, 3, 1), "p1")
        assert engine.get_tier("alice", date(2024, 3, 1)) == Tier.GOLD


# ===========================================================================
# 5. Point expiration
# ===========================================================================

class TestPointExpiration:
    def test_points_expire_after_90_days(self):
        engine = make_engine_with_customer(signup_date=date(2024, 1, 10))
        engine.record_purchase("alice", 100, date(2024, 3, 1), "p1")
        # Day 90 – still valid
        assert engine.get_balance("alice", date(2024, 3, 1) + timedelta(days=90)) == 100
        # Day 91 – expired
        assert engine.get_balance("alice", date(2024, 3, 1) + timedelta(days=91)) == 0

    def test_signup_month_points_never_expire(self):
        signup = date(2024, 1, 10)
        engine = make_engine_with_customer(signup_date=signup)
        # Purchase IN signup month (January 2024)
        engine.record_purchase("alice", 100, date(2024, 1, 15), "p1")
        # Check 5 years later
        assert engine.get_balance("alice", date(2029, 1, 15)) == 100

    def test_signup_month_first_day_never_expires(self):
        signup = date(2024, 6, 1)
        engine = make_engine_with_customer(signup_date=signup)
        engine.record_purchase("alice", 50, date(2024, 6, 1), "p1")
        assert engine.get_balance("alice", date(2025, 6, 1)) == 50

    def test_signup_month_last_day_never_expires(self):
        signup = date(2024, 6, 30)
        engine = make_engine_with_customer(signup_date=signup)
        engine.record_purchase("alice", 50, date(2024, 6, 30), "p1")
        assert engine.get_balance("alice", date(2025, 6, 30)) == 50

    def test_purchase_outside_signup_month_expires(self):
        signup = date(2024, 1, 10)
        engine = make_engine_with_customer(signup_date=signup)
        # Purchase in Feb 2024 (not signup month)
        engine.record_purchase("alice", 100, date(2024, 2, 1), "p1")
        assert engine.get_balance("alice", date(2024, 2, 1) + timedelta(days=91)) == 0

    def test_mixed_batches_expiry(self):
        """One expired batch and one valid; only valid counted."""
        signup = date(2024, 1, 10)
        engine = make_engine_with_customer(signup_date=signup)
        engine.record_purchase("alice", 100, date(2024, 3, 1), "p1")  # will expire
        engine.record_purchase("alice", 200, date(2024, 6, 1), "p2")  # still valid

        # Check 95 days after p1 but only 5 days after p2
        check_date = date(2024, 6, 4)   # p1 earned 2024-03-01, 95 days later = 2024-06-04
        # p1: (2024-06-04 - 2024-03-01).days = 95 > 90 → expired
        # p2: (2024-06-04 - 2024-06-01).days = 3 ≤ 90 → valid
        assert engine.get_balance("alice", check_date) == 200

    def test_exactly_90_days_not_yet_expired(self):
        engine = make_engine_with_customer(signup_date=date(2024, 1, 10))
        engine.record_purchase("alice", 100, date(2024, 3, 1), "p1")
        assert engine.get_balance("alice", date(2024, 3, 1) + timedelta(days=90)) == 100

    def test_91_days_expired(self):
        engine = make_engine_with_customer(signup_date=date(2024, 1, 10))
        engine.record_purchase("alice", 100, date(2024, 3, 1), "p1")
        assert engine.get_balance("alice", date(2024, 3, 1) + timedelta(days=91)) == 0


# ===========================================================================
# 6. Refunds
# ===========================================================================

class TestRefunds:
    def test_refund_claws_back_unspent_points(self):
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 100, date(2024, 3, 1), "p1")
        clawed = engine.record_refund("p1", date(2024, 3, 5))
        assert clawed == 100
        assert engine.get_balance("alice", date(2024, 3, 5)) == 0

    def test_refund_claws_back_only_remaining(self):
        """After spending some points, refund only claws back what's left."""
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 100, date(2024, 3, 1), "p1")
        engine.spend_points("alice", 60, date(2024, 3, 2))  # spend 60 of 100
        clawed = engine.record_refund("p1", date(2024, 3, 5))
        assert clawed == 40
        assert engine.get_balance("alice", date(2024, 3, 5)) == 0

    def test_refund_after_all_points_spent(self):
        """If all points are spent, refund claws back 0."""
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 100, date(2024, 3, 1), "p1")
        engine.spend_points("alice", 100, date(2024, 3, 2))
        clawed = engine.record_refund("p1", date(2024, 3, 5))
        assert clawed == 0

    def test_double_refund_raises(self):
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 100, date(2024, 3, 1), "p1")
        engine.record_refund("p1", date(2024, 3, 5))
        with pytest.raises(ValueError, match="already been refunded"):
            engine.record_refund("p1", date(2024, 3, 6))

    def test_refund_unknown_purchase_raises(self):
        engine = make_engine_with_customer()
        with pytest.raises(ValueError, match="not found"):
            engine.record_refund("nonexistent", date(2024, 3, 5))

    def test_refund_does_not_affect_other_batches(self):
        """Refunding p1 should not affect points from p2."""
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 100, date(2024, 3, 1), "p1")
        engine.record_purchase("alice", 200, date(2024, 3, 2), "p2")
        engine.record_refund("p1", date(2024, 3, 5))
        assert engine.get_balance("alice", date(2024, 3, 5)) == 200

    def test_refund_removes_spend_from_tier_calc(self):
        """Refund causes the spend to stop counting toward tier."""
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 1_500, date(2024, 3, 1), "p1")
        assert engine.get_tier("alice", date(2024, 3, 2)) == Tier.SILVER
        engine.record_refund("p1", date(2024, 3, 5))
        assert engine.get_tier("alice", date(2024, 3, 6)) == Tier.BRONZE

    def test_refund_partial_spend_across_multiple_purchases(self):
        """Spending draws from p1 first; p1 refund claws back its remainder."""
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 100, date(2024, 3, 1), "p1")  # 100 pts
        engine.record_purchase("alice", 100, date(2024, 3, 2), "p2")  # 100 pts
        # Spend 120 → drains p1 (100) and 20 from p2
        engine.spend_points("alice", 120, date(2024, 3, 3))
        # p1 now has 0, p2 has 80
        clawed = engine.record_refund("p1", date(2024, 3, 4))
        assert clawed == 0   # p1 was fully drained
        assert engine.get_balance("alice", date(2024, 3, 4)) == 80   # only p2 remains


# ===========================================================================
# 7. Spending points
# ===========================================================================

class TestSpendingPoints:
    def test_successful_spend(self):
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 300, date(2024, 3, 1), "p1")  # 300 pts
        success, balance = engine.spend_points("alice", 100, date(2024, 3, 5))
        assert success is True
        assert balance == 200

    def test_spend_full_balance(self):
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 200, date(2024, 3, 1), "p1")
        success, balance = engine.spend_points("alice", 200, date(2024, 3, 5))
        assert success is True
        assert balance == 0

    def test_spend_more_than_balance_rejected(self):
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 100, date(2024, 3, 1), "p1")
        success, balance = engine.spend_points("alice", 150, date(2024, 3, 5))
        assert success is False
        assert balance == 100   # unchanged

    def test_spend_zero_raises(self):
        engine = make_engine_with_customer()
        with pytest.raises(ValueError, match="positive"):
            engine.spend_points("alice", 0, date(2024, 3, 5))

    def test_spend_negative_raises(self):
        engine = make_engine_with_customer()
        with pytest.raises(ValueError, match="positive"):
            engine.spend_points("alice", -5, date(2024, 3, 5))

    def test_oldest_batch_consumed_first(self):
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 100, date(2024, 3, 1), "p1")  # older
        engine.record_purchase("alice", 100, date(2024, 3, 2), "p2")  # newer

        engine.spend_points("alice", 100, date(2024, 3, 5))

        # p1 should be drained, p2 should be untouched
        customer = engine._customers["alice"]
        batches = {b.purchase_id: b for b in customer.point_batches}
        assert batches["p1"].remaining_points == 0
        assert batches["p2"].remaining_points == 100

    def test_spend_skips_expired_batches(self):
        engine = make_engine_with_customer(signup_date=date(2024, 1, 10))
        engine.record_purchase("alice", 100, date(2024, 3, 1), "p1")  # expires
        engine.record_purchase("alice", 200, date(2024, 6, 1), "p2")  # valid

        spend_date = date(2024, 6, 4)  # p1 is 95 days old → expired
        success, balance = engine.spend_points("alice", 150, spend_date)
        assert success is True
        # p2 should go from 200 to 50
        assert balance == 50

    def test_spend_across_multiple_batches(self):
        engine = make_engine_with_customer()
        engine.record_purchase("alice", 100, date(2024, 3, 1), "p1")  # 100 pts
        engine.record_purchase("alice", 100, date(2024, 3, 2), "p2")  # 100 pts
        engine.record_purchase("alice", 100, date(2024, 3, 3), "p3")  # 100 pts
        success, balance = engine.spend_points("alice", 250, date(2024, 3, 10))
        assert success is True
        assert balance == 50

    def test_spend_does_not_touch_expired_older_batch(self):
        """Expired oldest batch is skipped; next valid batch is consumed."""
        engine = make_engine_with_customer(signup_date=date(2024, 1, 10))
        engine.record_purchase("alice", 50, date(2024, 3, 1), "p1")   # will expire
        engine.record_purchase("alice", 200, date(2024, 6, 1), "p2")  # valid

        spend_date = date(2024, 6, 4)   # p1 expired
        success, balance = engine.spend_points("alice", 50, spend_date)
        assert success is True
        assert balance == 150  # 200 - 50

    def test_no_points_balance_zero(self):
        engine = make_engine_with_customer()
        assert engine.get_balance("alice", date(2024, 3, 1)) == 0
        success, balance = engine.spend_points("alice", 1, date(2024, 3, 1))
        assert success is False
        assert balance == 0


# ===========================================================================
# 8. Trailing-365-day spend window
# ===========================================================================

class TestTrailingSpendWindow:
    def test_purchase_exactly_365_days_old_included(self):
        """Boundary: purchase exactly 365 days ago is still within the window."""
        engine = make_engine_with_customer()
        as_of = date(2025, 3, 1)
        purchase_date = as_of - timedelta(days=365)
        engine.record_purchase("alice", 1_000, purchase_date, "p1")
        # Should be included → Silver
        assert engine.get_tier("alice", as_of) == Tier.SILVER

    def test_purchase_366_days_old_excluded(self):
        engine = make_engine_with_customer()
        as_of = date(2025, 3, 1)
        purchase_date = as_of - timedelta(days=366)
        engine.record_purchase("alice", 1_000, purchase_date, "p1")
        # Excluded → Bronze
        assert engine.get_tier("alice", as_of) == Tier.BRONZE

    def test_multiple_purchases_some_outside_window(self):
        engine = make_engine_with_customer()
        as_of = date(2025, 3, 1)
        engine.record_purchase("alice", 4_000, as_of - timedelta(days=400), "p1")  # outside
        engine.record_purchase("alice", 1_500, as_of - timedelta(days=10), "p2")   # inside
        assert engine.get_tier("alice", as_of) == Tier.SILVER


# ===========================================================================
# 9. Integration / combined scenarios
# ===========================================================================

class TestIntegration:
    def test_full_lifecycle(self):
        """Register → buy → tier up → spend → refund → re-check."""
        engine = LoyaltyEngine()
        engine.register_customer("carol", date(2024, 2, 15))

        # Bronze purchase
        pts1, tier1 = engine.record_purchase("carol", 500, date(2024, 4, 1), "p1")
        assert tier1 == Tier.BRONZE
        assert pts1 == 500

        # Purchase that crosses into Silver ($500 + $600 = $1100 trailing)
        pts2, tier2 = engine.record_purchase("carol", 600, date(2024, 4, 10), "p2")
        assert tier2 == Tier.SILVER
        assert pts2 == 750   # 600 * 1.25

        balance = engine.get_balance("carol", date(2024, 4, 10))
        assert balance == 1250   # 500 + 750

        # Spend some
        ok, remaining = engine.spend_points("carol", 400, date(2024, 4, 15))
        assert ok is True
        assert remaining == 850

        # Refund p1 (500 points earned; 400 spent from p1 first → 100 left)
        clawed = engine.record_refund("p1", date(2024, 4, 20))
        assert clawed == 100
        assert engine.get_balance("carol", date(2024, 4, 20)) == 750

    def test_signup_month_points_survive_expiry_window(self):
        """Points earned in signup month coexist with expiring regular points."""
        engine = LoyaltyEngine()
        engine.register_customer("dave", date(2024, 5, 1))

        # Signup-month purchase
        engine.record_purchase("dave", 100, date(2024, 5, 10), "p1")  # never expires
        # Regular purchase in a different month (not signup month)
        engine.record_purchase("dave", 100, date(2024, 6, 1), "p2")  # will expire

        far_future = date(2024, 6, 1) + timedelta(days=91)
        # p2 should be expired; p1 should remain
        assert engine.get_balance("dave", far_future) == 100

    def test_tier_after_refund_drops_back(self):
        engine = LoyaltyEngine()
        engine.register_customer("eve", date(2024, 1, 1))
        engine.record_purchase("eve", 5_100, date(2024, 3, 1), "p1")
        assert engine.get_tier("eve", date(2024, 3, 2)) == Tier.GOLD
        engine.record_refund("p1", date(2024, 3, 5))
        assert engine.get_tier("eve", date(2024, 3, 6)) == Tier.BRONZE

    def test_spend_rejected_leaves_balance_intact(self):
        engine = LoyaltyEngine()
        engine.register_customer("frank", date(2024, 1, 1))
        engine.record_purchase("frank", 200, date(2024, 3, 1), "p1")  # 200 pts
        # Attempt to overspend
        ok, bal = engine.spend_points("frank", 300, date(2024, 3, 5))
        assert ok is False
        assert bal == 200
        # Balance unchanged
        assert engine.get_balance("frank", date(2024, 3, 5)) == 200

    def test_points_consumed_oldest_first_across_many_batches(self):
        """Verify oldest-first ordering with 4 batches."""
        engine = LoyaltyEngine()
        engine.register_customer("gina", date(2024, 1, 1))
        dates = [date(2024, 3, d) for d in (1, 5, 10, 20)]
        for i, d in enumerate(dates):
            engine.record_purchase("gina", 100, d, f"p{i+1}")
        # Total 400 pts; spend 250
        engine.spend_points("gina", 250, date(2024, 3, 25))
        customer = engine._customers["gina"]
        batches = sorted(customer.point_batches, key=lambda b: b.earned_date)
        # First 2 batches drained, third partially, fourth untouched
        assert batches[0].remaining_points == 0   # p1
        assert batches[1].remaining_points == 0   # p2
        assert batches[2].remaining_points == 50  # p3 (100 - 50)
        assert batches[3].remaining_points == 100 # p4

    def test_two_customers_are_independent(self):
        engine = LoyaltyEngine()
        engine.register_customer("h1", date(2024, 1, 1))
        engine.register_customer("h2", date(2024, 1, 1))
        engine.record_purchase("h1", 500, date(2024, 3, 1), "pa")
        engine.record_purchase("h2", 1_500, date(2024, 3, 1), "pb")
        assert engine.get_tier("h1", date(2024, 3, 2)) == Tier.BRONZE
        assert engine.get_tier("h2", date(2024, 3, 2)) == Tier.SILVER
        assert engine.get_balance("h1", date(2024, 3, 2)) == 500
        assert engine.get_balance("h2", date(2024, 3, 2)) == 1_875  # 1500 * 1.25

    def test_refund_claw_back_does_not_affect_points_in_other_batch(self):
        """Refund of p1 cannot create negative balance; p2 points are untouched."""
        engine = LoyaltyEngine()
        engine.register_customer("ivan", date(2024, 1, 1))
        engine.record_purchase("ivan", 100, date(2024, 3, 1), "p1")  # 100 pts
        engine.record_purchase("ivan", 50, date(2024, 3, 2), "p2")   # 50 pts
        # Spend 120 (takes all 100 from p1, 20 from p2)
        engine.spend_points("ivan", 120, date(2024, 3, 3))
        clawed = engine.record_refund("p1", date(2024, 3, 4))
        assert clawed == 0   # p1 fully spent, no claw-back
        assert engine.get_balance("ivan", date(2024, 3, 4)) == 30  # only p2 remainder

    def test_zero_points_purchase_can_be_refunded(self):
        """Edge: $0.49 * 1.0 = 0.49 → floor 0 points; refund returns 0."""
        engine = LoyaltyEngine()
        engine.register_customer("jill", date(2024, 1, 1))
        pts, _ = engine.record_purchase("jill", 0.49, date(2024, 3, 1), "p1")
        assert pts == 0
        clawed = engine.record_refund("p1", date(2024, 3, 2))
        assert clawed == 0

    def test_get_tier_and_balance_consistent_dates(self):
        """get_tier and get_balance as-of queries are date-accurate."""
        engine = LoyaltyEngine()
        engine.register_customer("kate", date(2024, 1, 1))
        engine.record_purchase("kate", 1_000, date(2024, 3, 1), "p1")
        # One day before the purchase: still Bronze, 0 balance
        # (but purchase date IS 2024-03-01, so on that date tier is Silver)
        assert engine.get_tier("kate", date(2024, 2, 28)) == Tier.BRONZE
        assert engine.get_balance("kate", date(2024, 2, 28)) == 0
        assert engine.get_tier("kate", date(2024, 3, 1)) == Tier.SILVER
        assert engine.get_balance("kate", date(2024, 3, 1)) == 1_250  # 1000 * 1.25


# ===========================================================================
# 10. PointBatch unit tests
# ===========================================================================

class TestPointBatch:
    def test_expired_flag_exact_boundary(self):
        signup = date(2024, 1, 1)
        batch = PointBatch(
            purchase_id="x",
            earned_date=date(2024, 3, 1),
            _signup_date=signup,
            original_points=100,
            remaining_points=100,
        )
        assert not batch.is_expired(date(2024, 3, 1) + timedelta(days=90))
        assert batch.is_expired(date(2024, 3, 1) + timedelta(days=91))

    def test_signup_month_batch_never_expired(self):
        signup = date(2024, 3, 10)
        batch = PointBatch(
            purchase_id="y",
            earned_date=date(2024, 3, 15),
            _signup_date=signup,
            original_points=50,
            remaining_points=50,
        )
        assert not batch.is_expired(date(2030, 1, 1))
