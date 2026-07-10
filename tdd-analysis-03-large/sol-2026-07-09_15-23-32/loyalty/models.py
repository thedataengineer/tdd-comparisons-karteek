"""Data models for the loyalty points engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class Tier(str, Enum):
    BRONZE = "Bronze"
    SILVER = "Silver"
    GOLD = "Gold"


# ── Tier thresholds (trailing-365-day spend) ──────────────────────────────────
TIER_THRESHOLDS = [
    (5_000.00, Tier.GOLD),
    (1_000.00, Tier.SILVER),
    (0.00, Tier.BRONZE),
]

# ── Points-per-dollar by tier ─────────────────────────────────────────────────
TIER_RATE = {
    Tier.BRONZE: 1.00,
    Tier.SILVER: 1.25,
    Tier.GOLD: 1.50,
}

# ── Expiration window ─────────────────────────────────────────────────────────
EXPIRY_DAYS = 90


def tier_for_spend(spend: float) -> Tier:
    """Return the tier that corresponds to *spend* dollars."""
    for threshold, tier in TIER_THRESHOLDS:
        if spend >= threshold:
            return tier
    return Tier.BRONZE  # unreachable but safe


# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class PointBatch:
    """A group of points awarded from a single purchase."""

    purchase_id: str
    earned_date: date
    original_points: int
    remaining_points: int
    never_expires: bool = False  # True for signup-month points

    def is_expired(self, as_of: date) -> bool:
        if self.never_expires:
            return False
        return (as_of - self.earned_date).days >= EXPIRY_DAYS

    def available(self, as_of: date) -> int:
        """Non-expired, un-spent points available on *as_of*."""
        if self.is_expired(as_of):
            return 0
        return self.remaining_points


@dataclass
class PurchaseRecord:
    """Internal record of a customer purchase."""

    purchase_id: str
    customer_id: str
    amount: float
    date: date
    points_earned: int
    refunded: bool = False


@dataclass
class Customer:
    """All state for a single customer."""

    customer_id: str
    signup_date: date
    purchases: list[PurchaseRecord] = field(default_factory=list)
    batches: list[PointBatch] = field(default_factory=list)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _trailing_spend(self, as_of: date) -> float:
        """Total spend (net of refunds) in the trailing 365 days ending *as_of*."""
        cutoff = as_of.replace(year=as_of.year - 1) if as_of.month != 2 or as_of.day != 29 else as_of.replace(year=as_of.year - 1, day=28)
        # Use timedelta for accurate 365-day window
        from datetime import timedelta
        cutoff = as_of - timedelta(days=365)
        total = 0.0
        for p in self.purchases:
            if not p.refunded and p.date >= cutoff and p.date <= as_of:
                total += p.amount
        return total

    def tier(self, as_of: date) -> Tier:
        """Current tier as of *as_of*."""
        return tier_for_spend(self._trailing_spend(as_of))

    def balance(self, as_of: date) -> int:
        """Total spendable (non-expired) points as of *as_of*."""
        return sum(b.available(as_of) for b in self.batches)

    def _is_signup_month(self, d: date) -> bool:
        return d.year == self.signup_date.year and d.month == self.signup_date.month


# ── Result types (returned to callers) ───────────────────────────────────────


@dataclass
class PurchaseResult:
    purchase_id: str
    points_earned: int
    tier: Tier


@dataclass
class RefundResult:
    purchase_id: str
    points_clawed_back: int


@dataclass
class SpendResult:
    success: bool
    remaining_balance: int
    message: str = ""
