from datetime import date
from loyalty.engine import LoyaltyEngine


def test_create_customer():
    engine = LoyaltyEngine()
    engine.create_customer("alice", signup_date=date(2024, 1, 1))
    tier = engine.get_tier("alice", as_of=date(2024, 1, 1))
    assert tier == "Bronze"


def test_bronze_purchase_earns_1_point_per_dollar():
    engine = LoyaltyEngine()
    engine.create_customer("alice", signup_date=date(2024, 1, 1))
    result = engine.record_purchase("alice", amount=100.0, purchase_date=date(2024, 6, 1))
    assert result["points_earned"] == 100
    assert result["tier"] == "Bronze"


def test_silver_purchase_earns_125_points_per_100_dollars():
    engine = LoyaltyEngine()
    engine.create_customer("bob", signup_date=date(2023, 1, 1))
    # Spend enough to reach Silver tier first
    engine.record_purchase("bob", amount=1000.0, purchase_date=date(2024, 1, 1), purchase_id="p1")
    # Now Bob is Silver; this purchase should earn at 1.25 rate
    result = engine.record_purchase("bob", amount=100.0, purchase_date=date(2024, 6, 1), purchase_id="p2")
    assert result["tier"] == "Silver"
    assert result["points_earned"] == 125


def test_gold_purchase_earns_150_points_per_100_dollars():
    engine = LoyaltyEngine()
    engine.create_customer("carol", signup_date=date(2023, 1, 1))
    engine.record_purchase("carol", amount=5000.0, purchase_date=date(2024, 1, 1), purchase_id="p1")
    result = engine.record_purchase("carol", amount=100.0, purchase_date=date(2024, 6, 1), purchase_id="p2")
    assert result["tier"] == "Gold"
    assert result["points_earned"] == 150


def test_tier_upgrade_applies_to_triggering_purchase():
    """A purchase that pushes spend to $1000 earns points at Silver rate."""
    engine = LoyaltyEngine()
    engine.create_customer("dave", signup_date=date(2023, 1, 1))
    # $900 puts Dave in Bronze still
    engine.record_purchase("dave", amount=900.0, purchase_date=date(2024, 1, 1), purchase_id="p1")
    # $100 more pushes total to $1000 -> Silver; should earn at Silver rate
    result = engine.record_purchase("dave", amount=100.0, purchase_date=date(2024, 6, 1), purchase_id="p2")
    assert result["tier"] == "Silver"
    assert result["points_earned"] == 125  # 100 * 1.25


def test_points_rounded_down():
    """Silver rate: $10 * 1.25 = 12.5 -> floor = 12"""
    engine = LoyaltyEngine()
    engine.create_customer("eve", signup_date=date(2023, 1, 1))
    engine.record_purchase("eve", amount=1000.0, purchase_date=date(2024, 1, 1), purchase_id="p1")
    result = engine.record_purchase("eve", amount=10.0, purchase_date=date(2024, 6, 1), purchase_id="p2")
    assert result["points_earned"] == 12


def test_get_balance_returns_total_unspent_points():
    engine = LoyaltyEngine()
    engine.create_customer("frank", signup_date=date(2023, 1, 1))
    engine.record_purchase("frank", amount=100.0, purchase_date=date(2024, 6, 1), purchase_id="p1")
    engine.record_purchase("frank", amount=200.0, purchase_date=date(2024, 6, 15), purchase_id="p2")
    balance = engine.get_balance("frank", as_of=date(2024, 6, 20))
    assert balance == 300  # 100 + 200


def test_points_expire_after_90_days():
    engine = LoyaltyEngine()
    engine.create_customer("grace", signup_date=date(2023, 1, 1))
    engine.record_purchase("grace", amount=100.0, purchase_date=date(2024, 1, 1), purchase_id="p1")
    # 91 days later: points should be expired
    balance = engine.get_balance("grace", as_of=date(2024, 4, 1))  # Jan 1 + 91 days = Apr 1
    assert balance == 0


def test_points_still_valid_at_90_days():
    engine = LoyaltyEngine()
    engine.create_customer("hank", signup_date=date(2023, 1, 1))
    engine.record_purchase("hank", amount=100.0, purchase_date=date(2024, 1, 1), purchase_id="p1")
    from datetime import timedelta
    balance = engine.get_balance("hank", as_of=date(2024, 1, 1) + timedelta(days=90))
    assert balance == 100


def test_signup_month_points_never_expire():
    engine = LoyaltyEngine()
    engine.create_customer("iris", signup_date=date(2024, 1, 15))
    # Purchase during signup month
    engine.record_purchase("iris", amount=100.0, purchase_date=date(2024, 1, 20), purchase_id="p1")
    # Check balance 200 days later — should still be 100
    from datetime import timedelta
    balance = engine.get_balance("iris", as_of=date(2024, 1, 20) + timedelta(days=200))
    assert balance == 100


def test_spend_points_success():
    engine = LoyaltyEngine()
    engine.create_customer("jack", signup_date=date(2023, 1, 1))
    engine.record_purchase("jack", amount=200.0, purchase_date=date(2024, 6, 1), purchase_id="p1")
    result = engine.spend_points("jack", points=50, spend_date=date(2024, 6, 10))
    assert result["success"] is True
    assert result["remaining_balance"] == 150


def test_spend_points_failure_insufficient_balance():
    engine = LoyaltyEngine()
    engine.create_customer("kate", signup_date=date(2023, 1, 1))
    engine.record_purchase("kate", amount=100.0, purchase_date=date(2024, 6, 1), purchase_id="p1")
    result = engine.spend_points("kate", points=200, spend_date=date(2024, 6, 10))
    assert result["success"] is False
    assert result["remaining_balance"] == 100


def test_spend_points_oldest_batch_first():
    engine = LoyaltyEngine()
    engine.create_customer("leo", signup_date=date(2023, 1, 1))
    engine.record_purchase("leo", amount=100.0, purchase_date=date(2024, 6, 1), purchase_id="p1")  # 100 pts (older)
    engine.record_purchase("leo", amount=200.0, purchase_date=date(2024, 6, 15), purchase_id="p2")  # 200 pts (newer)
    engine.spend_points("leo", points=100, spend_date=date(2024, 6, 20))
    # The 100 pts from p1 should be depleted; p2 still has 200
    p1_batch = engine._purchases["p1"]["points_batches"][0]
    p2_batch = engine._purchases["p2"]["points_batches"][0]
    assert p1_batch["remaining"] == 0
    assert p2_batch["remaining"] == 200


def test_spend_points_skips_expired_batches():
    engine = LoyaltyEngine()
    engine.create_customer("mia", signup_date=date(2023, 1, 1))
    # Old batch (will expire)
    engine.record_purchase("mia", amount=100.0, purchase_date=date(2024, 1, 1), purchase_id="p1")
    # New batch (still valid)
    engine.record_purchase("mia", amount=50.0, purchase_date=date(2024, 6, 1), purchase_id="p2")
    # On Aug 1 2024: p1 is ~212 days old (expired), p2 is ~61 days (valid)
    result = engine.spend_points("mia", points=30, spend_date=date(2024, 8, 1))
    assert result["success"] is True
    p1_batch = engine._purchases["p1"]["points_batches"][0]
    p2_batch = engine._purchases["p2"]["points_batches"][0]
    assert p1_batch["remaining"] == 100  # untouched (expired)
    assert p2_batch["remaining"] == 20   # 50 - 30


def test_refund_claws_back_points():
    engine = LoyaltyEngine()
    engine.create_customer("nina", signup_date=date(2023, 1, 1))
    engine.record_purchase("nina", amount=100.0, purchase_date=date(2024, 6, 1), purchase_id="p1")
    result = engine.record_refund("p1", refund_date=date(2024, 6, 10))
    assert result["points_clawed_back"] == 100
    balance = engine.get_balance("nina", as_of=date(2024, 6, 10))
    assert balance == 0


def test_refund_only_claws_back_unspent_points():
    engine = LoyaltyEngine()
    engine.create_customer("omar", signup_date=date(2023, 1, 1))
    engine.record_purchase("omar", amount=100.0, purchase_date=date(2024, 6, 1), purchase_id="p1")
    # Spend 40 of the 100 points
    engine.spend_points("omar", points=40, spend_date=date(2024, 6, 5))
    # Refund the purchase — should only claw back 60
    result = engine.record_refund("p1", refund_date=date(2024, 6, 10))
    assert result["points_clawed_back"] == 60
    balance = engine.get_balance("omar", as_of=date(2024, 6, 10))
    assert balance == 0


def test_refund_does_not_affect_other_purchases():
    engine = LoyaltyEngine()
    engine.create_customer("pat", signup_date=date(2023, 1, 1))
    engine.record_purchase("pat", amount=100.0, purchase_date=date(2024, 6, 1), purchase_id="p1")
    engine.record_purchase("pat", amount=200.0, purchase_date=date(2024, 6, 10), purchase_id="p2")
    engine.record_refund("p1", refund_date=date(2024, 6, 15))
    balance = engine.get_balance("pat", as_of=date(2024, 6, 15))
    assert balance == 200


def test_purchase_can_only_be_refunded_once():
    engine = LoyaltyEngine()
    engine.create_customer("quinn", signup_date=date(2023, 1, 1))
    engine.record_purchase("quinn", amount=100.0, purchase_date=date(2024, 6, 1), purchase_id="p1")
    engine.record_refund("p1", refund_date=date(2024, 6, 10))
    import pytest
    with pytest.raises(ValueError):
        engine.record_refund("p1", refund_date=date(2024, 6, 15))


def test_refund_reduces_trailing_spend_and_tier():
    engine = LoyaltyEngine()
    engine.create_customer("rosa", signup_date=date(2023, 1, 1))
    # Push Rosa to Silver
    engine.record_purchase("rosa", amount=1000.0, purchase_date=date(2024, 6, 1), purchase_id="p1")
    assert engine.get_tier("rosa", as_of=date(2024, 6, 1)) == "Silver"
    # Refund that purchase — she should drop back to Bronze
    engine.record_refund("p1", refund_date=date(2024, 6, 10))
    assert engine.get_tier("rosa", as_of=date(2024, 6, 10)) == "Bronze"


def test_trailing_spend_excludes_purchases_older_than_365_days():
    engine = LoyaltyEngine()
    engine.create_customer("sam", signup_date=date(2022, 1, 1))
    # Big purchase 366 days ago — should not count
    engine.record_purchase("sam", amount=5000.0, purchase_date=date(2023, 1, 1), purchase_id="p1")
    # Check tier 366 days later
    from datetime import timedelta
    check_date = date(2023, 1, 1) + timedelta(days=366)
    assert engine.get_tier("sam", as_of=check_date) == "Bronze"


def test_spend_points_across_multiple_batches_stops_at_zero():
    """Spending exactly fills first batch, then deducts from second, then stops."""
    engine = LoyaltyEngine()
    engine.create_customer("tia", signup_date=date(2023, 1, 1))
    engine.record_purchase("tia", amount=50.0, purchase_date=date(2024, 6, 1), purchase_id="p1")   # 50 pts
    engine.record_purchase("tia", amount=100.0, purchase_date=date(2024, 6, 10), purchase_id="p2")  # 100 pts
    engine.record_purchase("tia", amount=200.0, purchase_date=date(2024, 6, 20), purchase_id="p3")  # 200 pts
    # Spend 120: depletes p1 (50) and takes 70 from p2
    result = engine.spend_points("tia", points=120, spend_date=date(2024, 6, 25))
    assert result["success"] is True
    assert engine._purchases["p1"]["points_batches"][0]["remaining"] == 0
    assert engine._purchases["p2"]["points_batches"][0]["remaining"] == 30
    assert engine._purchases["p3"]["points_batches"][0]["remaining"] == 200
