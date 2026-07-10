from datetime import date, timedelta
from math import floor
from typing import Any
import uuid

TIER_RATES = {"Bronze": 1.0, "Silver": 1.25, "Gold": 1.5}


def _compute_tier(trailing_spend: float) -> str:
    if trailing_spend >= 5000:
        return "Gold"
    elif trailing_spend >= 1000:
        return "Silver"
    return "Bronze"


class LoyaltyEngine:
    def __init__(self):
        self._customers: dict[str, dict[str, Any]] = {}
        self._purchases: dict[str, dict[str, Any]] = {}

    def create_customer(self, customer_id: str, signup_date: date):
        self._customers[customer_id] = {
            "signup_date": signup_date,
            "purchases": [],  # list of purchase_ids in order
        }

    def _trailing_spend(self, customer_id: str, as_of: date) -> float:
        cutoff = as_of - timedelta(days=365)
        total = 0.0
        for pid in self._customers[customer_id]["purchases"]:
            p = self._purchases[pid]
            if p.get("refunded"):
                continue
            if p["date"] > cutoff:
                total += p["amount"]
        return total

    def get_tier(self, customer_id: str, as_of: date) -> str:
        spend = self._trailing_spend(customer_id, as_of)
        return _compute_tier(spend)

    def record_purchase(
        self, customer_id: str, amount: float, purchase_date: date, purchase_id: str = None
    ) -> dict:
        if purchase_id is None:
            purchase_id = str(uuid.uuid4())
        customer = self._customers[customer_id]

        # Add purchase to list so trailing spend includes it
        self._purchases[purchase_id] = {
            "id": purchase_id,
            "customer_id": customer_id,
            "amount": amount,
            "date": purchase_date,
            "refunded": False,
            "points_batches": [],  # list of point-batch dicts
        }
        customer["purchases"].append(purchase_id)

        # Tier is computed AFTER including this purchase
        tier = self.get_tier(customer_id, as_of=purchase_date)
        rate = TIER_RATES[tier]
        points = floor(amount * rate)

        # Record points batch
        signup_date = customer["signup_date"]
        is_signup_month = (
            purchase_date.year == signup_date.year
            and purchase_date.month == signup_date.month
        )
        batch = {
            "purchase_id": purchase_id,
            "points": points,
            "remaining": points,
            "earned_date": purchase_date,
            "never_expire": is_signup_month,
        }
        self._purchases[purchase_id]["points_batches"] = [batch]
        self._purchases[purchase_id]["points_earned"] = points

        return {"purchase_id": purchase_id, "points_earned": points, "tier": tier}

    def _is_batch_expired(self, batch: dict, as_of: date) -> bool:
        if batch["never_expire"]:
            return False
        return (as_of - batch["earned_date"]).days > 90

    def get_balance(self, customer_id: str, as_of: date) -> int:
        total = 0
        for pid in self._customers[customer_id]["purchases"]:
            p = self._purchases[pid]
            for batch in p["points_batches"]:
                if not self._is_batch_expired(batch, as_of):
                    total += batch["remaining"]
        return total

    def spend_points(self, customer_id: str, points: int, spend_date: date) -> dict:
        balance = self.get_balance(customer_id, as_of=spend_date)
        if points > balance:
            return {"success": False, "remaining_balance": balance}

        to_deduct = points
        for pid in self._customers[customer_id]["purchases"]:
            if to_deduct == 0:
                break
            p = self._purchases[pid]
            for batch in p["points_batches"]:
                if to_deduct == 0:
                    break
                if self._is_batch_expired(batch, spend_date):
                    continue
                take = min(batch["remaining"], to_deduct)
                batch["remaining"] -= take
                to_deduct -= take

        remaining = self.get_balance(customer_id, as_of=spend_date)
        return {"success": True, "remaining_balance": remaining}

    def record_refund(self, purchase_id: str, refund_date: date) -> dict:
        p = self._purchases[purchase_id]
        if p["refunded"]:
            raise ValueError(f"Purchase {purchase_id} has already been refunded.")

        # Claw back whatever remains in the batch (points not yet spent)
        clawed_back = 0
        for batch in p["points_batches"]:
            clawed_back += batch["remaining"]
            batch["remaining"] = 0
        p["refunded"] = True
        return {"points_clawed_back": clawed_back}

