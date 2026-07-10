"""Comprehensive tests for the loyalty points engine."""

import pytest
from datetime import date, timedelta

from loyalty import LoyaltyEngine, Tier, PurchaseResult, RefundResult, SpendResult
from loyalty.models import EXPIRY_DAYS, tier_for_spend


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    return LoyaltyEngine()


@pytest.fixture
def alice(engine):
    """A customer signed up on 2024-01-15 (January 2024)."""
    engine.register_customer("alice", date(2024, 1, 15))
    return engine


@pytest.fixture
def bob(engine):
    """A customer signed up on 2024-06-01."""
    engine.register_customer("bob", date(2024, 6, 1))
    return engine


# ═══════════════════════════════════════════════════════════════════════════════
# Customer registration
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegistration:
    def test_register_success(self, engine):
        engine.register_customer("c1", date(2024, 1, 1))
        # No exception means success

    def test_register_duplicate_raises(self, engine):
        engine.register_customer("c1", date(2024, 1, 1))
        with pytest.raises(ValueError, match="already registered"):
            engine.register_customer("c1", date(2024, 1, 1))

    def test_unknown_customer_raises_on_purchase(self, engine):
        with pytest.raises(ValueError, match="Unknown customer"):
            engine.record_purchase("nobody", "p1", 100.0, date(2024, 2, 1))

    def test_unknown_customer_raises_on_get_balance(self, engine):
        with pytest.raises(ValueError, match="Unknown customer"):
            engine.get_balance("nobody", date(2024, 2, 1))

    def test_unknown_customer_raises_on_get_tier(self, engine):
        with pytest.raises(ValueError, match="Unknown customer"):
            engine.get_tier("nobody", date(2024, 2, 1))

    def test_unknown_customer_raises_on_spend(self, engine):
        with pytest.raises(ValueError, match="Unknown customer"):
            engine.spend_points("nobody", 10, date(2024, 2, 1))


# ═══════════════════════════════════════════════════════════════════════════════
# Tier logic
# ═══════════════════════════════════════════════════════════════════════════════

class TestTierThresholds:
    def test_tier_for_spend_bronze(self):
        assert tier_for_spend(0) == Tier.BRONZE
        assert tier_for_spend(999.99) == Tier.BRONZE

    def test_tier_for_spend_silver(self):
        assert tier_for_spend(1000.00) == Tier.SILVER
        assert tier_for_spend(4999.99) == Tier.SILVER

    def test_tier_for_spend_gold(self):
        assert tier_for_spend(5000.00) == Tier.GOLD
        assert tier_for_spend(999_999) == Tier.GOLD

    def test_initial_tier_is_bronze(self, alice):
        assert alice.get_tier("alice", date(2024, 2, 1)) == Tier.BRONZE

    def test_tier_after_silver_threshold(self, alice):
        alice.record_purchase("alice", "p1", 1000.00, date(2024, 2, 1))
        assert alice.get_tier("alice", date(2024, 2, 1)) == Tier.SILVER

    def test_tier_after_gold_threshold(self, alice):
        alice.record_purchase("alice", "p1", 5000.00, date(2024, 2, 1))
        assert alice.get_tier("alice", date(2024, 2, 1)) == Tier.GOLD

    def test_tier_drops_when_old_purchases_fall_outside_365_days(self, alice):
        """Spend that was in the trailing window but now ages out should drop tier."""
        # Push alice to Silver in Jan 2024
        alice.record_purchase("alice", "p1", 1000.00, date(2024, 2, 1))
        assert alice.get_tier("alice", date(2024, 2, 1)) == Tier.SILVER
        # Check tier 366 days later — the purchase is now outside the window
        future = date(2024, 2, 1) + timedelta(days=366)
        assert alice.get_tier("alice", future) == Tier.BRONZE

    def test_tier_trailing_365_days_boundary(self, alice):
        """A purchase exactly 365 days ago is still in the window."""
        ref_date = date(2025, 2, 1)
        purchase_date = ref_date - timedelta(days=365)
        alice.record_purchase("alice", "p1", 1000.00, purchase_date)
        assert alice.get_tier("alice", ref_date) == Tier.SILVER

    def test_tier_trailing_366_days_excluded(self, alice):
        """A purchase 366 days ago is outside the trailing window."""
        ref_date = date(2025, 2, 1)
        purchase_date = ref_date - timedelta(days=366)
        alice.record_purchase("alice", "p1", 1000.00, purchase_date)
        assert alice.get_tier("alice", ref_date) == Tier.BRONZE


# ═══════════════════════════════════════════════════════════════════════════════
# Earning points
# ═══════════════════════════════════════════════════════════════════════════════

class TestEarningPoints:
    def test_bronze_rate(self, alice):
        result = alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))
        assert result.points_earned == 100
        assert result.tier == Tier.BRONZE

    def test_silver_rate(self, alice):
        # First purchase pushes to Silver, earns at Silver rate
        result = alice.record_purchase("alice", "p1", 1000.00, date(2024, 2, 1))
        assert result.tier == Tier.SILVER
        assert result.points_earned == 1250  # 1000 * 1.25

    def test_gold_rate(self, alice):
        result = alice.record_purchase("alice", "p1", 5000.00, date(2024, 2, 1))
        assert result.tier == Tier.GOLD
        assert result.points_earned == 7500  # 5000 * 1.5

    def test_points_rounded_down(self, alice):
        # 1 * 1.25 = 1.25 → floor = 1
        result = alice.record_purchase("alice", "p1", 1000.00, date(2024, 2, 1))
        # $1000 at Silver = 1250 (exact); test with an odd amount
        result2 = alice.record_purchase("alice", "p2", 1.00, date(2024, 2, 1))
        # Still Silver; 1 * 1.25 = 1.25 → floor = 1
        assert result2.points_earned == 1

    def test_points_rounded_down_gold(self, alice):
        alice.record_purchase("alice", "p1", 5000.00, date(2024, 2, 1))  # push to gold
        result = alice.record_purchase("alice", "p2", 1.00, date(2024, 2, 2))
        # 1 * 1.5 = 1.5 → floor = 1
        assert result.points_earned == 1

    def test_tier_upgrade_applies_to_triggering_purchase(self, alice):
        """If a purchase pushes from Bronze → Silver, points are at Silver rate."""
        # Alice starts at Bronze; $1000 purchase pushes to Silver
        result = alice.record_purchase("alice", "p1", 1000.00, date(2024, 2, 1))
        assert result.tier == Tier.SILVER
        assert result.points_earned == 1250

    def test_tier_upgrade_bronze_to_gold_in_one_purchase(self, alice):
        """$5000 purchase moves directly from Bronze to Gold."""
        result = alice.record_purchase("alice", "p1", 5000.00, date(2024, 2, 1))
        assert result.tier == Tier.GOLD
        assert result.points_earned == 7500

    def test_balance_accumulates(self, alice):
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))
        alice.record_purchase("alice", "p2", 200.00, date(2024, 2, 2))
        assert alice.get_balance("alice", date(2024, 2, 2)) == 300

    def test_zero_amount_purchase(self, alice):
        result = alice.record_purchase("alice", "p1", 0.00, date(2024, 2, 1))
        assert result.points_earned == 0

    def test_negative_amount_raises(self, alice):
        with pytest.raises(ValueError, match="negative"):
            alice.record_purchase("alice", "p1", -10.00, date(2024, 2, 1))

    def test_duplicate_purchase_id_raises(self, alice):
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))
        with pytest.raises(ValueError, match="already exists"):
            alice.record_purchase("alice", "p1", 200.00, date(2024, 2, 2))

    def test_purchase_result_fields(self, alice):
        result = alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))
        assert isinstance(result, PurchaseResult)
        assert result.purchase_id == "p1"
        assert result.points_earned == 100
        assert result.tier == Tier.BRONZE


# ═══════════════════════════════════════════════════════════════════════════════
# Point expiration
# ═══════════════════════════════════════════════════════════════════════════════

class TestExpiration:
    def test_points_valid_before_90_days(self, alice):
        alice.record_purchase("alice", "p1", 100.00, date(2024, 3, 1))
        check = date(2024, 3, 1) + timedelta(days=89)
        assert alice.get_balance("alice", check) == 100

    def test_points_expired_at_90_days(self, alice):
        alice.record_purchase("alice", "p1", 100.00, date(2024, 3, 1))
        check = date(2024, 3, 1) + timedelta(days=90)
        assert alice.get_balance("alice", check) == 0

    def test_points_expired_after_90_days(self, alice):
        alice.record_purchase("alice", "p1", 100.00, date(2024, 3, 1))
        check = date(2024, 3, 1) + timedelta(days=91)
        assert alice.get_balance("alice", check) == 0

    def test_signup_month_points_never_expire(self, alice):
        """Points earned during signup month (Jan 2024) never expire."""
        # alice signed up 2024-01-15, purchase in Jan 2024
        alice.record_purchase("alice", "p1", 100.00, date(2024, 1, 20))
        far_future = date(2025, 6, 1)  # well past 90 days
        assert alice.get_balance("alice", far_future) == 100

    def test_signup_month_boundary_same_month_year(self, alice):
        """Purchase on signup month but different day still never expires."""
        alice.record_purchase("alice", "p1", 50.00, date(2024, 1, 1))
        far_future = date(2025, 1, 1)
        assert alice.get_balance("alice", far_future) == 50

    def test_non_signup_month_points_expire(self, alice):
        """Points earned outside signup month (Jan 2024) do expire."""
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))
        check = date(2024, 2, 1) + timedelta(days=90)
        assert alice.get_balance("alice", check) == 0

    def test_mix_of_expiring_and_non_expiring(self, alice):
        """Signup-month batch persists while non-signup batches expire."""
        alice.record_purchase("alice", "p1", 100.00, date(2024, 1, 20))  # never expires
        alice.record_purchase("alice", "p2", 200.00, date(2024, 2, 1))   # expires
        # After p2 expires
        check = date(2024, 2, 1) + timedelta(days=90)
        assert alice.get_balance("alice", check) == 100  # only p1 batch remains

    def test_different_batches_expire_independently(self, alice):
        alice.record_purchase("alice", "p1", 100.00, date(2024, 3, 1))
        alice.record_purchase("alice", "p2", 50.00, date(2024, 4, 1))
        # p1 expires at 90 days from 2024-03-01 = 2024-05-29
        after_p1_expires = date(2024, 3, 1) + timedelta(days=90)
        assert alice.get_balance("alice", after_p1_expires) == 50  # only p2
        # p2 expires at 90 days from 2024-04-01 = 2024-06-30
        after_p2_expires = date(2024, 4, 1) + timedelta(days=90)
        assert alice.get_balance("alice", after_p2_expires) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Refunds
# ═══════════════════════════════════════════════════════════════════════════════

class TestRefunds:
    def test_refund_full_unspent_batch(self, alice):
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))
        result = alice.record_refund("p1", date(2024, 2, 5))
        assert isinstance(result, RefundResult)
        assert result.purchase_id == "p1"
        assert result.points_clawed_back == 100
        assert alice.get_balance("alice", date(2024, 2, 5)) == 0

    def test_refund_partially_spent_batch(self, alice):
        """Only remaining (un-spent) points are clawed back."""
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))
        alice.spend_points("alice", 40, date(2024, 2, 2))
        result = alice.record_refund("p1", date(2024, 2, 5))
        assert result.points_clawed_back == 60  # 100 - 40 spent
        assert alice.get_balance("alice", date(2024, 2, 5)) == 0

    def test_refund_fully_spent_batch_claws_nothing(self, alice):
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))
        alice.spend_points("alice", 100, date(2024, 2, 2))
        result = alice.record_refund("p1", date(2024, 2, 5))
        assert result.points_clawed_back == 0

    def test_refund_does_not_affect_other_batches(self, alice):
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))
        alice.record_purchase("alice", "p2", 200.00, date(2024, 2, 2))
        alice.record_refund("p1", date(2024, 2, 5))
        assert alice.get_balance("alice", date(2024, 2, 5)) == 200

    def test_refund_unknown_purchase_raises(self, alice):
        with pytest.raises(ValueError, match="Unknown purchase"):
            alice.record_refund("nonexistent", date(2024, 2, 5))

    def test_refund_twice_raises(self, alice):
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))
        alice.record_refund("p1", date(2024, 2, 5))
        with pytest.raises(ValueError, match="already been refunded"):
            alice.record_refund("p1", date(2024, 2, 6))

    def test_refund_reduces_trailing_spend(self, alice):
        """Refund should drop trailing spend, potentially reducing tier."""
        alice.record_purchase("alice", "p1", 1000.00, date(2024, 2, 1))
        assert alice.get_tier("alice", date(2024, 2, 1)) == Tier.SILVER
        alice.record_refund("p1", date(2024, 2, 5))
        assert alice.get_tier("alice", date(2024, 2, 5)) == Tier.BRONZE

    def test_refund_with_spend_across_multiple_batches(self, alice):
        """Spend draws from p1, refund p2 only claws back p2's unspent points."""
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))  # 100 pts
        alice.record_purchase("alice", "p2", 200.00, date(2024, 2, 2))  # 200 pts
        # Spend 150 — draws 100 from p1, 50 from p2
        alice.spend_points("alice", 150, date(2024, 2, 3))
        # p2 has 150 remaining (200 - 50)
        result = alice.record_refund("p2", date(2024, 2, 4))
        assert result.points_clawed_back == 150

    def test_refund_result_type(self, alice):
        alice.record_purchase("alice", "p1", 50.00, date(2024, 2, 1))
        result = alice.record_refund("p1", date(2024, 2, 2))
        assert isinstance(result, RefundResult)


# ═══════════════════════════════════════════════════════════════════════════════
# Spending points
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpending:
    def test_spend_success(self, alice):
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))
        result = alice.spend_points("alice", 50, date(2024, 2, 2))
        assert result.success is True
        assert result.remaining_balance == 50

    def test_spend_full_balance(self, alice):
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))
        result = alice.spend_points("alice", 100, date(2024, 2, 2))
        assert result.success is True
        assert result.remaining_balance == 0

    def test_spend_more_than_balance_fails(self, alice):
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))
        result = alice.spend_points("alice", 101, date(2024, 2, 2))
        assert result.success is False
        assert result.remaining_balance == 100
        assert "Insufficient" in result.message

    def test_spend_zero_succeeds(self, alice):
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))
        result = alice.spend_points("alice", 0, date(2024, 2, 2))
        assert result.success is True
        assert result.remaining_balance == 100

    def test_spend_oldest_batch_first(self, alice):
        """Spending should draw from older batches first."""
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))  # 100 pts
        alice.record_purchase("alice", "p2", 200.00, date(2024, 2, 10))  # 200 pts
        alice.spend_points("alice", 100, date(2024, 2, 11))
        # p1 should be fully consumed
        result = alice.record_refund("p1", date(2024, 2, 12))
        assert result.points_clawed_back == 0  # p1 is empty

    def test_spend_skips_expired_batch(self, alice):
        """When oldest batch is expired, spending should skip it."""
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))  # will expire
        alice.record_purchase("alice", "p2", 50.00, date(2024, 3, 1))   # fresh

        # 90 days after p1: p1 is expired
        spend_date = date(2024, 2, 1) + timedelta(days=90)
        result = alice.spend_points("alice", 50, spend_date)
        assert result.success is True
        # p2 should be drained by 50
        assert alice.get_balance("alice", spend_date) == 0

    def test_spend_across_multiple_batches(self, alice):
        alice.record_purchase("alice", "p1", 60.00, date(2024, 2, 1))
        alice.record_purchase("alice", "p2", 60.00, date(2024, 2, 2))
        result = alice.spend_points("alice", 100, date(2024, 2, 3))
        assert result.success is True
        assert result.remaining_balance == 20

    def test_spend_result_type(self, alice):
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))
        result = alice.spend_points("alice", 50, date(2024, 2, 2))
        assert isinstance(result, SpendResult)

    def test_spend_negative_amount_raises(self, alice):
        with pytest.raises(ValueError, match="negative"):
            alice.spend_points("alice", -5, date(2024, 2, 1))

    def test_spend_cannot_spend_expired_points(self, alice):
        """Expired points count as 0 for balance; can't spend them."""
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))
        expired_date = date(2024, 2, 1) + timedelta(days=90)
        result = alice.spend_points("alice", 1, expired_date)
        assert result.success is False
        assert result.remaining_balance == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Balance queries
# ═══════════════════════════════════════════════════════════════════════════════

class TestBalanceQueries:
    def test_initial_balance_zero(self, alice):
        assert alice.get_balance("alice", date(2024, 2, 1)) == 0

    def test_balance_reflects_purchases(self, alice):
        alice.record_purchase("alice", "p1", 300.00, date(2024, 2, 1))
        assert alice.get_balance("alice", date(2024, 2, 1)) == 300

    def test_balance_after_spend(self, alice):
        alice.record_purchase("alice", "p1", 300.00, date(2024, 2, 1))
        alice.spend_points("alice", 100, date(2024, 2, 2))
        assert alice.get_balance("alice", date(2024, 2, 2)) == 200

    def test_balance_excludes_expired(self, alice):
        alice.record_purchase("alice", "p1", 100.00, date(2024, 3, 1))
        assert alice.get_balance("alice", date(2024, 3, 1) + timedelta(days=90)) == 0

    def test_balance_unknown_customer_raises(self, engine):
        with pytest.raises(ValueError):
            engine.get_balance("ghost", date(2024, 2, 1))


# ═══════════════════════════════════════════════════════════════════════════════
# Tier queries
# ═══════════════════════════════════════════════════════════════════════════════

class TestTierQueries:
    def test_tier_unknown_customer_raises(self, engine):
        with pytest.raises(ValueError):
            engine.get_tier("ghost", date(2024, 2, 1))

    def test_tier_without_purchases_is_bronze(self, alice):
        assert alice.get_tier("alice", date(2024, 2, 1)) == Tier.BRONZE

    def test_tier_changes_with_cumulative_spend(self, alice):
        alice.record_purchase("alice", "p1", 500.00, date(2024, 2, 1))
        assert alice.get_tier("alice", date(2024, 2, 1)) == Tier.BRONZE
        alice.record_purchase("alice", "p2", 500.00, date(2024, 2, 2))
        assert alice.get_tier("alice", date(2024, 2, 2)) == Tier.SILVER

    def test_tier_after_refund_drops(self, alice):
        alice.record_purchase("alice", "p1", 5000.00, date(2024, 2, 1))
        assert alice.get_tier("alice", date(2024, 2, 1)) == Tier.GOLD
        alice.record_refund("p1", date(2024, 2, 5))
        assert alice.get_tier("alice", date(2024, 2, 5)) == Tier.BRONZE


# ═══════════════════════════════════════════════════════════════════════════════
# Edge cases and integration scenarios
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    def test_full_lifecycle(self, engine):
        """Purchase → spend → refund interaction."""
        engine.register_customer("carol", date(2024, 3, 1))
        # Earn
        r1 = engine.record_purchase("carol", "p1", 200.00, date(2024, 3, 10))
        assert r1.points_earned == 200
        r2 = engine.record_purchase("carol", "p2", 100.00, date(2024, 3, 15))
        assert r2.points_earned == 100
        # Spend some
        s = engine.spend_points("carol", 150, date(2024, 3, 20))
        assert s.success is True
        assert s.remaining_balance == 150
        # Refund p1 (100 of its 200 pts were spent, so 100 clawed back)
        ref = engine.record_refund("p1", date(2024, 3, 22))
        assert ref.points_clawed_back == 50  # 200 - 150 spent from p1
        assert engine.get_balance("carol", date(2024, 3, 22)) == 100

    def test_tier_upgrade_mid_history(self, engine):
        """Customer crosses Silver threshold; next purchase earns at Silver."""
        engine.register_customer("dave", date(2024, 1, 1))
        engine.record_purchase("dave", "p1", 900.00, date(2024, 2, 1))
        assert engine.get_tier("dave", date(2024, 2, 1)) == Tier.BRONZE
        # This purchase tips them into Silver
        r = engine.record_purchase("dave", "p2", 100.00, date(2024, 2, 2))
        assert r.tier == Tier.SILVER
        assert r.points_earned == 125  # 100 * 1.25

    def test_multiple_customers_isolated(self, engine):
        engine.register_customer("e1", date(2024, 1, 1))
        engine.register_customer("e2", date(2024, 1, 1))
        engine.record_purchase("e1", "pA", 500.00, date(2024, 2, 1))
        engine.record_purchase("e2", "pB", 200.00, date(2024, 2, 1))
        assert engine.get_balance("e1", date(2024, 2, 1)) == 500
        assert engine.get_balance("e2", date(2024, 2, 1)) == 200

    def test_signup_month_does_not_affect_other_customers_signup_month(self, engine):
        engine.register_customer("f1", date(2024, 1, 1))
        engine.register_customer("f2", date(2024, 3, 1))
        # f1 earns in January (signup month) — never expires
        engine.record_purchase("f1", "p1", 100.00, date(2024, 1, 15))
        # f2 earns in January (NOT their signup month) — expires
        engine.record_purchase("f2", "p2", 100.00, date(2024, 1, 15))
        far = date(2024, 1, 15) + timedelta(days=90)
        assert engine.get_balance("f1", far) == 100
        assert engine.get_balance("f2", far) == 0

    def test_spend_then_check_refund_is_zero_when_fully_spent(self, alice):
        alice.record_purchase("alice", "p1", 10.00, date(2024, 2, 1))
        alice.spend_points("alice", 10, date(2024, 2, 2))
        result = alice.record_refund("p1", date(2024, 2, 3))
        assert result.points_clawed_back == 0
        assert alice.get_balance("alice", date(2024, 2, 3)) == 0

    def test_purchase_on_exact_trailing_edge(self, alice):
        """Purchase exactly at the 365-day cutoff boundary."""
        as_of = date(2025, 3, 1)
        purchase_date = as_of - timedelta(days=365)
        alice.record_purchase("alice", "p1", 1000.00, purchase_date)
        # Included: trailing span is [as_of - 365, as_of]
        assert alice.get_tier("alice", as_of) == Tier.SILVER

    def test_spend_uses_correct_batch_ordering(self, alice):
        """Three batches; spending should empty oldest batches first."""
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))  # 100 pts
        alice.record_purchase("alice", "p2", 100.00, date(2024, 2, 5))  # 100 pts
        alice.record_purchase("alice", "p3", 100.00, date(2024, 2, 10)) # 100 pts
        alice.spend_points("alice", 250, date(2024, 2, 11))
        # p1 and p2 fully spent; p3 has 50 left
        assert alice.get_balance("alice", date(2024, 2, 11)) == 50
        # Refund p3 — should only claw back 50
        res = alice.record_refund("p3", date(2024, 2, 12))
        assert res.points_clawed_back == 50

    def test_tier_is_bronze_with_no_trailing_spend_despite_old_purchase(self, alice):
        """Old purchase (>365 days ago) does not count toward tier."""
        old_date = date(2024, 1, 1)
        alice.record_purchase("alice", "p1", 2000.00, old_date)
        check_date = old_date + timedelta(days=366)
        assert alice.get_tier("alice", check_date) == Tier.BRONZE

    def test_gold_customer_fractional_points(self, alice):
        """Gold rate 1.5; odd amounts floor correctly."""
        alice.record_purchase("alice", "p1", 5000.00, date(2024, 2, 1))  # Gold
        result = alice.record_purchase("alice", "p2", 3.00, date(2024, 2, 2))
        # 3 * 1.5 = 4.5 → 4
        assert result.points_earned == 4

    def test_refund_of_spend_spanning_two_batches(self, alice):
        """Spend draws from p1 and p2; then refund p2 claws only p2's remainder."""
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))  # 100
        alice.record_purchase("alice", "p2", 100.00, date(2024, 2, 2))  # 100
        # Spend 120: 100 from p1, 20 from p2
        alice.spend_points("alice", 120, date(2024, 2, 3))
        # Refund p2: should claw back 80 (100 - 20 spent)
        result = alice.record_refund("p2", date(2024, 2, 4))
        assert result.points_clawed_back == 80
        assert alice.get_balance("alice", date(2024, 2, 4)) == 0  # p1=0, p2=0

    def test_no_negative_balance_after_refund_then_spend(self, alice):
        """Clawback never creates a negative balance."""
        alice.record_purchase("alice", "p1", 100.00, date(2024, 2, 1))
        alice.spend_points("alice", 100, date(2024, 2, 2))  # Fully spent
        alice.record_refund("p1", date(2024, 2, 3))  # 0 clawed back
        # Balance should remain 0, not negative
        assert alice.get_balance("alice", date(2024, 2, 3)) == 0
