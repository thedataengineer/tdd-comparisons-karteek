"""Loyalty Points Engine — core implementation."""

from __future__ import annotations

import math
from datetime import date
from typing import Dict

from .models import (
    Customer,
    PointBatch,
    PurchaseRecord,
    PurchaseResult,
    RefundResult,
    SpendResult,
    Tier,
    tier_for_spend,
    TIER_RATE,
)


class LoyaltyEngine:
    """
    In-memory loyalty points engine.

    Typical usage::

        engine = LoyaltyEngine()
        engine.register_customer("alice", date(2024, 3, 15))
        result = engine.record_purchase("alice", "p1", 1200.00, date(2024, 3, 20))
        # result.points_earned, result.tier

    All *date* arguments must be :class:`datetime.date` instances.
    """

    def __init__(self) -> None:
        # customer_id → Customer
        self._customers: Dict[str, Customer] = {}
        # purchase_id → (customer_id, PurchaseRecord)  — for fast lookup
        self._purchase_index: Dict[str, tuple[str, PurchaseRecord]] = {}

    # ── Customer registration ─────────────────────────────────────────────────

    def register_customer(self, customer_id: str, signup_date: date) -> None:
        """Create a new customer.  Raises ValueError if ID already exists."""
        if customer_id in self._customers:
            raise ValueError(f"Customer '{customer_id}' already registered.")
        self._customers[customer_id] = Customer(
            customer_id=customer_id,
            signup_date=signup_date,
        )

    # ── Purchases ─────────────────────────────────────────────────────────────

    def record_purchase(
        self,
        customer_id: str,
        purchase_id: str,
        amount: float,
        purchase_date: date,
    ) -> PurchaseResult:
        """
        Record a purchase and award points.

        :returns: :class:`PurchaseResult` with *points_earned* and resulting *tier*.
        :raises ValueError: unknown customer / duplicate purchase id / negative amount.
        """
        if customer_id not in self._customers:
            raise ValueError(f"Unknown customer '{customer_id}'.")
        if purchase_id in self._purchase_index:
            raise ValueError(f"Purchase ID '{purchase_id}' already exists.")
        if amount < 0:
            raise ValueError("Purchase amount cannot be negative.")

        customer = self._customers[customer_id]

        # 1. Create a preliminary PurchaseRecord (not yet refunded).
        record = PurchaseRecord(
            purchase_id=purchase_id,
            customer_id=customer_id,
            amount=amount,
            date=purchase_date,
            points_earned=0,  # filled below
        )
        customer.purchases.append(record)
        self._purchase_index[purchase_id] = (customer_id, record)

        # 2. Recalculate tier *after* this purchase is included in trailing spend.
        new_tier = customer.tier(purchase_date)

        # 3. Calculate points at the new tier rate (rounded down).
        rate = TIER_RATE[new_tier]
        points = math.floor(amount * rate)
        record.points_earned = points

        # 4. Create a PointBatch for these points.
        never_expires = customer._is_signup_month(purchase_date)
        batch = PointBatch(
            purchase_id=purchase_id,
            earned_date=purchase_date,
            original_points=points,
            remaining_points=points,
            never_expires=never_expires,
        )
        customer.batches.append(batch)

        return PurchaseResult(
            purchase_id=purchase_id,
            points_earned=points,
            tier=new_tier,
        )

    # ── Refunds ───────────────────────────────────────────────────────────────

    def record_refund(self, purchase_id: str, refund_date: date) -> RefundResult:
        """
        Refund a purchase: claws back any un-spent points from that purchase.

        :returns: :class:`RefundResult` with *points_clawed_back*.
        :raises ValueError: unknown / already-refunded purchase id.
        """
        if purchase_id not in self._purchase_index:
            raise ValueError(f"Unknown purchase ID '{purchase_id}'.")

        customer_id, record = self._purchase_index[purchase_id]
        if record.refunded:
            raise ValueError(f"Purchase '{purchase_id}' has already been refunded.")

        customer = self._customers[customer_id]

        # Find the associated PointBatch.
        batch = self._get_batch(customer, purchase_id)

        # Claw back remaining (un-spent) points from this batch only.
        clawed_back = batch.remaining_points
        batch.remaining_points = 0

        # Mark purchase as refunded (removes it from trailing spend).
        record.refunded = True

        return RefundResult(purchase_id=purchase_id, points_clawed_back=clawed_back)

    # ── Spending ──────────────────────────────────────────────────────────────

    def spend_points(
        self, customer_id: str, amount: int, spend_date: date
    ) -> SpendResult:
        """
        Deduct *amount* points from the customer's balance (oldest-batch-first).

        Points are only deducted if the full *amount* is available (no partial
        spend).  Expired batches are skipped.

        :returns: :class:`SpendResult`.
        :raises ValueError: unknown customer.
        """
        if customer_id not in self._customers:
            raise ValueError(f"Unknown customer '{customer_id}'.")
        if amount < 0:
            raise ValueError("Spend amount cannot be negative.")

        customer = self._customers[customer_id]
        current_balance = customer.balance(spend_date)

        if amount > current_balance:
            return SpendResult(
                success=False,
                remaining_balance=current_balance,
                message=f"Insufficient points: requested {amount}, available {current_balance}.",
            )

        # Consume oldest-batch-first (batches are appended in chronological order).
        remaining = amount
        for batch in customer.batches:
            if remaining == 0:
                break
            if batch.is_expired(spend_date) or batch.remaining_points == 0:
                continue
            deduct = min(batch.remaining_points, remaining)
            batch.remaining_points -= deduct
            remaining -= deduct

        return SpendResult(
            success=True,
            remaining_balance=customer.balance(spend_date),
        )

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_balance(self, customer_id: str, as_of: date) -> int:
        """Return the customer's current spendable point balance as of *as_of*."""
        if customer_id not in self._customers:
            raise ValueError(f"Unknown customer '{customer_id}'.")
        return self._customers[customer_id].balance(as_of)

    def get_tier(self, customer_id: str, as_of: date) -> Tier:
        """Return the customer's tier as of *as_of*."""
        if customer_id not in self._customers:
            raise ValueError(f"Unknown customer '{customer_id}'.")
        return self._customers[customer_id].tier(as_of)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_batch(self, customer: Customer, purchase_id: str) -> PointBatch:
        for batch in customer.batches:
            if batch.purchase_id == purchase_id:
                return batch
        raise RuntimeError(
            f"Internal inconsistency: no batch found for purchase '{purchase_id}'."
        )
