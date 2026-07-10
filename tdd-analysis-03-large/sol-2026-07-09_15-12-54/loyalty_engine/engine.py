from datetime import date, timedelta
from dataclasses import dataclass, field
from typing import Optional

TIER_RATES = {"Bronze": 1.0, "Silver": 1.25, "Gold": 1.5}
TIER_THRESHOLDS = [(5000, "Gold"), (1000, "Silver"), (0, "Bronze")]


@dataclass
class PointBatch:
    purchase_id: str
    earned: int
    remaining: int
    earned_date: date
    signup_month: bool  # True if earned during signup month -> never expires

    def is_expired(self, as_of: date) -> bool:
        if self.signup_month:
            return False
        return (as_of - self.earned_date).days > 90


@dataclass
class Purchase:
    purchase_id: str
    customer_id: str
    amount: float
    purchase_date: date
    points_earned: int
    refunded: bool = False


@dataclass
class Customer:
    customer_id: str
    signup_date: date
    tier: str = "Bronze"
    total_spend_trailing: float = 0.0  # recomputed as needed
    batches: list = field(default_factory=list)  # list[PointBatch]


def _tier_for_spend(spend: float) -> str:
    for threshold, tier in TIER_THRESHOLDS:
        if spend >= threshold:
            return tier
    return "Bronze"


class LoyaltyEngine:
    def __init__(self):
        self._customers: dict[str, Customer] = {}
        self._purchases: dict[str, Purchase] = {}

    def create_customer(self, customer_id: str, signup_date: date) -> None:
        self._customers[customer_id] = Customer(customer_id, signup_date)

    def _trailing_spend(self, customer_id: str, as_of: date) -> float:
        cutoff = as_of - timedelta(days=365)
        total = 0.0
        for p in self._purchases.values():
            if p.customer_id == customer_id and not p.refunded:
                if p.purchase_date > cutoff:
                    total += p.amount
        return total

    def record_purchase(self, customer_id: str, purchase_id: str, amount: float,
                        purchase_date: date) -> dict:
        customer = self._customers[customer_id]
        # Calculate trailing spend including this purchase
        trailing = self._trailing_spend(customer_id, purchase_date) + amount
        tier = _tier_for_spend(trailing)
        customer.tier = tier

        rate = TIER_RATES[tier]
        points = int(amount * rate)  # floor

        # Determine if this purchase is in signup month
        signup_month = (purchase_date.year == customer.signup_date.year and
                        purchase_date.month == customer.signup_date.month)

        batch = PointBatch(
            purchase_id=purchase_id,
            earned=points,
            remaining=points,
            earned_date=purchase_date,
            signup_month=signup_month,
        )
        customer.batches.append(batch)

        purchase = Purchase(
            purchase_id=purchase_id,
            customer_id=customer_id,
            amount=amount,
            purchase_date=purchase_date,
            points_earned=points,
        )
        self._purchases[purchase_id] = purchase

        return {"points_earned": points, "tier": tier}

    def get_tier(self, customer_id: str, as_of: date) -> str:
        customer = self._customers[customer_id]
        trailing = self._trailing_spend(customer_id, as_of)
        return _tier_for_spend(trailing)

    def record_refund(self, purchase_id: str, refund_date: date) -> dict:
        purchase = self._purchases[purchase_id]
        if purchase.refunded:
            raise ValueError(f"Purchase {purchase_id} already refunded")
        purchase.refunded = True
        customer = self._customers[purchase.customer_id]
        # Find the batch for this purchase and claw back remaining points
        clawed_back = 0
        for batch in customer.batches:
            if batch.purchase_id == purchase_id:
                clawed_back = batch.remaining
                batch.remaining = 0
                break
        return {"points_clawed_back": clawed_back}

    def spend_points(self, customer_id: str, amount: int, as_of: date) -> dict:
        customer = self._customers[customer_id]
        balance = self.get_balance(customer_id, as_of)
        if amount > balance:
            return {"success": False, "remaining_balance": balance}
        # Consume oldest batches first, skipping expired
        to_consume = amount
        for batch in sorted(customer.batches, key=lambda b: b.earned_date):
            if batch.is_expired(as_of):
                continue
            if to_consume <= 0:
                break
            deduct = min(batch.remaining, to_consume)
            batch.remaining -= deduct
            to_consume -= deduct
        remaining = self.get_balance(customer_id, as_of)
        return {"success": True, "remaining_balance": remaining}

    def get_balance(self, customer_id: str, as_of: date) -> int:
        customer = self._customers[customer_id]
        total = 0
        for batch in customer.batches:
            if not batch.is_expired(as_of):
                total += batch.remaining
        return total
