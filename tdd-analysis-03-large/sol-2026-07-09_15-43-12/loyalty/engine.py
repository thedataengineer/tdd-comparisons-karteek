"""
Loyalty Points Engine
=====================
In-memory loyalty points system supporting:
  - Tiered point earning (Bronze / Silver / Gold)
  - Rolling 90-day point expiration (signup-month batches never expire)
  - Purchase refunds with targeted point claw-back
  - Oldest-first point spending
  - Trailing-365-day spend for tier calculation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Tier definition
# ---------------------------------------------------------------------------

class Tier(Enum):
    BRONZE = "Bronze"
    SILVER = "Silver"
    GOLD = "Gold"


_TIER_RATES: Dict[Tier, float] = {
    Tier.BRONZE: 1.00,
    Tier.SILVER: 1.25,
    Tier.GOLD: 1.50,
}


def _tier_for_spend(total_spend: float) -> Tier:
    """Return the tier that corresponds to a trailing-365-day spend amount."""
    if total_spend >= 5_000.00:
        return Tier.GOLD
    if total_spend >= 1_000.00:
        return Tier.SILVER
    return Tier.BRONZE


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PointBatch:
    """
    Represents points earned from a single purchase.

    Points expire 90 days after ``earned_date`` unless the purchase was made
    during the customer's signup month (same calendar month + year), in which
    case they never expire.
    """
    purchase_id: str
    earned_date: date
    _signup_date: date          # stored privately; used only for expiry logic
    original_points: int
    remaining_points: int

    def _is_signup_month_batch(self) -> bool:
        return (
            self.earned_date.year == self._signup_date.year
            and self.earned_date.month == self._signup_date.month
        )

    def is_expired(self, as_of: date) -> bool:
        """Return True if this batch has fully expired as of *as_of*."""
        if self._is_signup_month_batch():
            return False
        return (as_of - self.earned_date).days > 90


@dataclass
class Purchase:
    """Internal record of a single purchase transaction."""
    purchase_id: str
    customer_id: str
    amount: float
    purchase_date: date
    points_earned: int
    refunded: bool = False


@dataclass
class Customer:
    """Holds all state for a single customer."""
    customer_id: str
    signup_date: date
    purchases: List[Purchase] = field(default_factory=list)
    point_batches: List[PointBatch] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _trailing_spend(self, as_of: date) -> float:
        """Sum of non-refunded purchase amounts in the trailing 365 days up to *as_of*."""
        cutoff = as_of - timedelta(days=365)
        return sum(
            p.amount
            for p in self.purchases
            if not p.refunded
            and p.purchase_date >= cutoff
            and p.purchase_date <= as_of
        )

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------

    def get_tier(self, as_of: date) -> Tier:
        """Return the customer's tier as of *as_of*, based on trailing spend."""
        return _tier_for_spend(self._trailing_spend(as_of))

    def get_balance(self, as_of: date) -> int:
        """Return the total spendable (non-expired) point balance as of *as_of*."""
        return sum(
            b.remaining_points
            for b in self.point_batches
            if b.earned_date <= as_of and not b.is_expired(as_of)
        )


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class LoyaltyEngine:
    """
    Central façade for the loyalty points system.

    Usage example::

        engine = LoyaltyEngine()
        engine.register_customer("alice", date(2024, 1, 15))
        points, tier = engine.record_purchase("alice", 800, date(2024, 3, 1), "p001")
        success, balance = engine.spend_points("alice", 200, date(2024, 3, 5))
    """

    def __init__(self) -> None:
        self._customers: Dict[str, Customer] = {}
        self._purchases: Dict[str, Purchase] = {}

    # ------------------------------------------------------------------
    # Customer registration
    # ------------------------------------------------------------------

    def register_customer(self, customer_id: str, signup_date: date) -> Customer:
        """
        Register a new customer.

        Parameters
        ----------
        customer_id:
            Unique identifier for the customer.
        signup_date:
            The date the customer signed up; used to determine the
            never-expiring signup-month point batch window.

        Returns
        -------
        Customer
            The newly created :class:`Customer` object.

        Raises
        ------
        ValueError
            If a customer with *customer_id* already exists.
        """
        if customer_id in self._customers:
            raise ValueError(f"Customer '{customer_id}' already exists.")
        customer = Customer(customer_id=customer_id, signup_date=signup_date)
        self._customers[customer_id] = customer
        return customer

    # ------------------------------------------------------------------
    # Purchase recording
    # ------------------------------------------------------------------

    def record_purchase(
        self,
        customer_id: str,
        amount: float,
        purchase_date: date,
        purchase_id: str,
    ) -> Tuple[int, Tier]:
        """
        Record a purchase and award points.

        The tier applied (and points earned) is determined **after** adding
        this purchase's spend to the trailing-365-day total.  A tier upgrade
        triggered by this very purchase takes effect immediately.

        Parameters
        ----------
        customer_id:
            The customer making the purchase.
        amount:
            Dollar amount of the purchase (must be > 0).
        purchase_date:
            Date of the purchase.
        purchase_id:
            Unique identifier for this purchase (used for refunds).

        Returns
        -------
        (points_earned, new_tier):
            ``points_earned`` is the whole number of points awarded (floor).
            ``new_tier`` is the tier that applies after this purchase.

        Raises
        ------
        ValueError
            If the customer does not exist, the amount is non-positive, or
            the purchase_id is already in use.
        """
        if customer_id not in self._customers:
            raise ValueError(f"Customer '{customer_id}' not found.")
        if amount <= 0:
            raise ValueError("Purchase amount must be positive.")
        if purchase_id in self._purchases:
            raise ValueError(f"Purchase ID '{purchase_id}' already exists.")

        customer = self._customers[customer_id]

        # Include this purchase's amount in the trailing-365-day window so
        # that a tier upgrade triggered by this purchase applies to it.
        cutoff = purchase_date - timedelta(days=365)
        prior_spend = sum(
            p.amount
            for p in customer.purchases
            if not p.refunded and p.purchase_date >= cutoff
        )
        total_spend = prior_spend + amount
        tier = _tier_for_spend(total_spend)
        rate = _TIER_RATES[tier]
        points = int(amount * rate)   # floor truncation

        purchase = Purchase(
            purchase_id=purchase_id,
            customer_id=customer_id,
            amount=amount,
            purchase_date=purchase_date,
            points_earned=points,
        )
        customer.purchases.append(purchase)
        self._purchases[purchase_id] = purchase

        batch = PointBatch(
            purchase_id=purchase_id,
            earned_date=purchase_date,
            _signup_date=customer.signup_date,
            original_points=points,
            remaining_points=points,
        )
        customer.point_batches.append(batch)

        return points, tier

    # ------------------------------------------------------------------
    # Refunds
    # ------------------------------------------------------------------

    def record_refund(self, purchase_id: str, refund_date: date) -> int:
        """
        Process a refund for a previously recorded purchase.

        Claws back however many of the original earned points are still
        remaining in that batch.  Already-spent points are not recovered
        from other batches; the balance simply cannot go negative.

        Parameters
        ----------
        purchase_id:
            The purchase being refunded.
        refund_date:
            Date of the refund (used to update tier).  Currently stored
            for completeness; tier is always recalculated on query.

        Returns
        -------
        int
            Number of points clawed back (may be 0 if all were already spent).

        Raises
        ------
        ValueError
            If the purchase does not exist or has already been refunded.
        """
        if purchase_id not in self._purchases:
            raise ValueError(f"Purchase '{purchase_id}' not found.")

        purchase = self._purchases[purchase_id]
        if purchase.refunded:
            raise ValueError(f"Purchase '{purchase_id}' has already been refunded.")

        customer = self._customers[purchase.customer_id]

        # Find the matching point batch.
        batch: Optional[PointBatch] = next(
            (b for b in customer.point_batches if b.purchase_id == purchase_id),
            None,
        )

        clawed_back = 0
        if batch is not None:
            clawed_back = batch.remaining_points
            batch.remaining_points = 0

        purchase.refunded = True
        return clawed_back

    # ------------------------------------------------------------------
    # Spending points
    # ------------------------------------------------------------------

    def spend_points(
        self,
        customer_id: str,
        points_to_spend: int,
        spend_date: date,
    ) -> Tuple[bool, int]:
        """
        Attempt to spend points from a customer's balance.

        Points are consumed oldest-batch-first, skipping fully-expired
        batches.  If the requested amount exceeds the available non-expired
        balance, the entire transaction is rejected (no partial spend).

        Parameters
        ----------
        customer_id:
            The customer spending points.
        points_to_spend:
            Number of points to spend (must be > 0).
        spend_date:
            The date on which the spend occurs (used for expiry checks).

        Returns
        -------
        (success, remaining_balance):
            ``success`` is True if the spend was applied, False otherwise.
            ``remaining_balance`` is the balance after the attempt.

        Raises
        ------
        ValueError
            If the customer does not exist or *points_to_spend* is not positive.
        """
        if customer_id not in self._customers:
            raise ValueError(f"Customer '{customer_id}' not found.")
        if points_to_spend <= 0:
            raise ValueError("Points to spend must be positive.")

        customer = self._customers[customer_id]
        balance = customer.get_balance(spend_date)

        if points_to_spend > balance:
            return False, balance

        remaining = points_to_spend
        # Consume oldest non-expired batches first.
        eligible = sorted(
            (b for b in customer.point_batches if not b.is_expired(spend_date) and b.remaining_points > 0),
            key=lambda b: b.earned_date,
        )

        for batch in eligible:
            if remaining <= 0:
                break
            take = min(remaining, batch.remaining_points)
            batch.remaining_points -= take
            remaining -= take

        return True, customer.get_balance(spend_date)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_balance(self, customer_id: str, as_of: date) -> int:
        """
        Return the customer's spendable point balance as of *as_of*.

        Parameters
        ----------
        customer_id:
            The customer to query.
        as_of:
            Expiry is evaluated relative to this date.

        Raises
        ------
        ValueError
            If the customer does not exist.
        """
        if customer_id not in self._customers:
            raise ValueError(f"Customer '{customer_id}' not found.")
        return self._customers[customer_id].get_balance(as_of)

    def get_tier(self, customer_id: str, as_of: date) -> Tier:
        """
        Return the customer's tier as of *as_of*.

        Parameters
        ----------
        customer_id:
            The customer to query.
        as_of:
            Trailing-365-day spend is evaluated up to this date.

        Raises
        ------
        ValueError
            If the customer does not exist.
        """
        if customer_id not in self._customers:
            raise ValueError(f"Customer '{customer_id}' not found.")
        return self._customers[customer_id].get_tier(as_of)
