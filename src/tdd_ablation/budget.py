"""Budget pilot calculations and censoring rules."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from tdd_ablation.contracts import ContractError

ALL_CONDITIONS = {"1", "2", "3", "4", "5", "6a", "6b", "6c"}
CENSORED_STATUSES = {"token_exhausted", "timed_out"}


@dataclass(frozen=True)
class PilotRun:
    condition_id: str
    tokens_used: int
    duration_seconds: float
    excluded_from_analysis: bool = True


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    condition_id: str
    exit_status: str


@dataclass(frozen=True)
class BudgetDecision:
    token_ceiling: int
    timeout_seconds: int
    provider_limit: int
    runtime_cap_seconds: int
    samples_per_condition: dict[str, int]


@dataclass(frozen=True)
class CensoringReport:
    total: int
    censored: int
    rate_by_condition: dict[str, float]
    requires_protocol_review: bool


def _validate_pilot_runs(pilot_runs: list[PilotRun]) -> dict[str, int]:
    if not pilot_runs:
        raise ContractError("pilot_runs list cannot be empty")

    counts = Counter(p.condition_id for p in pilot_runs)
    for cond in ALL_CONDITIONS:
        if counts[cond] < 12:
            raise ContractError(
                f"each condition requires at least 12 pilot runs, condition {cond!r} has {counts[cond]}"
            )
        if not all(p.excluded_from_analysis for p in pilot_runs if p.condition_id == cond):
            raise ContractError("pilot runs must have excluded_from_analysis=True")

    return dict(counts)


def shared_token_ceiling(pilot_runs: list[PilotRun], provider_limit: int) -> int:
    """Calculate shared token ceiling from largest condition max + 20% margin."""
    _validate_pilot_runs(pilot_runs)
    if provider_limit <= 0:
        raise ContractError("provider_limit must be positive")

    max_tokens_by_cond = {
        cond: max(p.tokens_used for p in pilot_runs if p.condition_id == cond)
        for cond in ALL_CONDITIONS
    }
    overall_max = max(max_tokens_by_cond.values())
    ceiling = math.ceil(overall_max * 1.20)
    return min(ceiling, provider_limit)


def shared_timeout(pilot_runs: list[PilotRun], runtime_cap_seconds: int) -> int:
    """Calculate shared timeout seconds from largest condition max + 20% margin."""
    _validate_pilot_runs(pilot_runs)
    if runtime_cap_seconds <= 0:
        raise ContractError("runtime_cap_seconds must be positive")

    max_time_by_cond = {
        cond: max(p.duration_seconds for p in pilot_runs if p.condition_id == cond)
        for cond in ALL_CONDITIONS
    }
    overall_max = max(max_time_by_cond.values())
    timeout = math.ceil(overall_max * 1.20)
    return min(timeout, runtime_cap_seconds)


def budget_decision(
    pilot_runs: list[PilotRun], provider_limit: int, runtime_cap_seconds: int
) -> BudgetDecision:
    """Compute and return full BudgetDecision object."""
    counts = _validate_pilot_runs(pilot_runs)
    ceiling = shared_token_ceiling(pilot_runs, provider_limit)
    timeout = shared_timeout(pilot_runs, runtime_cap_seconds)
    return BudgetDecision(
        token_ceiling=ceiling,
        timeout_seconds=timeout,
        provider_limit=provider_limit,
        runtime_cap_seconds=runtime_cap_seconds,
        samples_per_condition=counts,
    )


def censoring_report(runs: list[RunRecord]) -> CensoringReport:
    """Calculate censoring rate by condition and check protocol review threshold (>10%)."""
    if not runs:
        raise ContractError("runs list cannot be empty")

    total = len(runs)
    censored_count = sum(1 for r in runs if r.exit_status in CENSORED_STATUSES)

    cond_total = Counter(r.condition_id for r in runs)
    cond_censored = Counter(r.condition_id for r in runs if r.exit_status in CENSORED_STATUSES)

    rates: dict[str, float] = {}
    review_required = False

    for cond, t_count in cond_total.items():
        c_count = cond_censored[cond]
        rate = c_count / t_count
        rates[cond] = rate
        if rate > 0.10:
            review_required = True

    return CensoringReport(
        total=total,
        censored=censored_count,
        rate_by_condition=rates,
        requires_protocol_review=review_required,
    )
