"""Pre-registration validation and normal-approximation power analysis."""

from __future__ import annotations

import math
from statistics import NormalDist
from typing import Any

from tdd_ablation.contracts import ContractError, require_fields


def validate_preregistration(data: dict[str, Any]) -> None:
    """Validate pre-registration dictionary structure and required fields."""
    require_fields(data, {"hypotheses", "confirmation_success"}, "preregistration")

    hypotheses = data.get("hypotheses")
    if not isinstance(hypotheses, list):
        raise ContractError("preregistration: hypotheses must be a list")

    for idx, hyp in enumerate(hypotheses):
        if not isinstance(hyp, dict):
            raise ContractError(f"preregistration: hypothesis[{idx}] must be a dict")
        require_fields(
            hyp,
            {
                "id",
                "claim",
                "baseline_condition",
                "treatment_condition",
                "primary_metric",
                "direction",
                "minimum_useful_effect",
                "alpha",
                "power",
            },
            f"preregistration: hypothesis[{idx}]",
        )

    confirmation_success = data.get("confirmation_success")
    if not isinstance(confirmation_success, dict):
        raise ContractError("preregistration: confirmation_success must be a dict")
    require_fields(
        confirmation_success,
        {
            "min_effect_point",
            "min_effect_ci_low",
            "max_severe_defect_rr_ci_high",
            "min_economic_value_ci_low",
        },
        "preregistration: confirmation_success",
    )


def required_runs(
    effect: float,
    standard_deviation: float,
    alpha: float = 0.05,
    power: float = 0.80,
    design_effect: float = 1.0,
    attrition: float = 0.0,
) -> int:
    """Calculate required sample size per condition arm using normal approximation.

    Applies design effect for task clustering and inflates for expected attrition.
    """
    if effect <= 0:
        raise ContractError("effect must be positive")
    if standard_deviation <= 0:
        raise ContractError("standard_deviation must be positive")
    if not (0 < alpha < 1):
        raise ContractError("alpha must be between 0 and 1")
    if not (0 < power < 1):
        raise ContractError("power must be between 0 and 1")
    if design_effect < 1.0:
        raise ContractError("design_effect must be >= 1.0")
    if not (0.0 <= attrition < 1.0):
        raise ContractError("attrition must be in [0, 1)")

    # Two-sample Z test sample size formula per arm:
    # n = 2 * ((z_{1-alpha/2} + z_{power}) * sigma / delta)^2
    dist = NormalDist()
    z_alpha = dist.inv_cdf(1 - alpha / 2)
    z_power = dist.inv_cdf(power)

    n_raw = 2 * (((z_alpha + z_power) * standard_deviation / effect) ** 2)
    n_clustered = n_raw * design_effect
    n_final = n_clustered / (1.0 - attrition)

    return math.ceil(n_final)
