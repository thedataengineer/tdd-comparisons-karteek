"""Statistical analysis, cluster bootstrap, Holm-Bonferroni correction, and confirmation decision rules."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

from tdd_ablation.budget import CensoringReport
from tdd_ablation.contracts import ContractError


@dataclass(frozen=True)
class CostModel:
    token_price_per_k: float
    review_cost_per_min: float
    defect_cost_by_severity: dict[str, float]
    delay_cost_per_hour: float

    def calculate_net_value(
        self,
        avoided_defects: dict[str, int],
        tokens_used: int,
        review_minutes: float,
        delay_hours: float,
    ) -> float:
        avoided_cost = sum(
            count * self.defect_cost_by_severity.get(sev, 0.0)
            for sev, count in avoided_defects.items()
        )
        token_cost = (tokens_used / 1000.0) * self.token_price_per_k
        review_cost = review_minutes * self.review_cost_per_min
        delay_cost = delay_hours * self.delay_cost_per_hour
        return avoided_cost - token_cost - review_cost - delay_cost


@dataclass(frozen=True)
class EffectEstimate:
    point: float
    low: float
    high: float


@dataclass(frozen=True)
class RiskRatioEstimate:
    point: float
    low: float
    high: float


@dataclass(frozen=True)
class InteractionResult:
    blocks_claim: bool
    p_value: float


@dataclass(frozen=True)
class Decision:
    adopt: bool
    reasons: list[str]


@dataclass(frozen=True)
class AnalysisRow:
    task_id: str
    condition_id: str
    variant_id: str
    score: float
    high_severity_defects: int
    is_censored: bool = False


def holm_bonferroni_adjust(p_values: list[float], alpha: float = 0.05) -> list[bool]:
    """Apply Holm-Bonferroni multiplicity correction to a list of p-values."""
    m = len(p_values)
    if m == 0:
        return []

    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    rejected = [False] * m

    for k, (orig_idx, p_val) in enumerate(indexed, start=1):
        threshold = alpha / (m - k + 1)
        if p_val <= threshold:
            rejected[orig_idx] = True
        else:
            break  # Stop at first non-rejection

    return rejected


def paired_effect(
    rows: list[AnalysisRow],
    baseline: str,
    treatment: str,
    seed: int,
    num_bootstraps: int = 1000,
) -> EffectEstimate:
    """Task-cluster bootstrap for paired difference in mean scores."""
    b_scores = [r.score for r in rows if r.condition_id == baseline]
    t_scores = [r.score for r in rows if r.condition_id == treatment]

    if not b_scores or not t_scores:
        raise ContractError(f"missing scores for baseline {baseline} or treatment {treatment}")

    task_ids = sorted(
        {r.task_id for r in rows if r.condition_id in {baseline, treatment}}
    )
    task_effects: list[float] = []
    for task_id in task_ids:
        task_baseline = [
            r.score for r in rows if r.task_id == task_id and r.condition_id == baseline
        ]
        task_treatment = [
            r.score for r in rows if r.task_id == task_id and r.condition_id == treatment
        ]
        if not task_baseline or not task_treatment:
            raise ContractError(f"missing paired scores for task {task_id}")
        task_effects.append(
            (sum(task_treatment) / len(task_treatment))
            - (sum(task_baseline) / len(task_baseline))
        )

    point_diff = sum(task_effects) / len(task_effects)

    rng = random.Random(seed)
    diffs: list[float] = []

    for _ in range(num_bootstraps):
        sampled_effects = [rng.choice(task_effects) for _ in task_effects]
        diffs.append(sum(sampled_effects) / len(sampled_effects))

    if not diffs:
        return EffectEstimate(point=point_diff, low=point_diff, high=point_diff)

    diffs.sort()
    low_idx = int(0.025 * len(diffs))
    high_idx = int(0.975 * len(diffs))

    return EffectEstimate(point=point_diff, low=diffs[low_idx], high=diffs[high_idx])


def prompt_interaction(
    rows: list[AnalysisRow],
    baseline: str,
    treatment: str,
    seed: int = 0,
    alpha: float = 0.05,
    num_permutations: int = 1000,
) -> InteractionResult:
    """Test whether treatment effect differs across prompt variants."""
    if not 0.0 < alpha < 1.0:
        raise ContractError("alpha must be between 0 and 1")
    if num_permutations <= 0:
        raise ContractError("num_permutations must be positive")

    grouped: dict[str, dict[str, dict[str, list[float]]]] = {}
    for row in rows:
        if row.condition_id not in {baseline, treatment}:
            continue
        grouped.setdefault(row.variant_id, {}).setdefault(row.task_id, {}).setdefault(
            row.condition_id, []
        ).append(row.score)

    variant_effects: dict[str, list[float]] = {}
    for variant_id, tasks in grouped.items():
        effects: list[float] = []
        for task_id, conditions in tasks.items():
            baseline_scores = conditions.get(baseline, [])
            treatment_scores = conditions.get(treatment, [])
            if not baseline_scores or not treatment_scores:
                raise ContractError(
                    f"missing paired scores for task {task_id}, variant {variant_id}"
                )
            effects.append(
                (sum(treatment_scores) / len(treatment_scores))
                - (sum(baseline_scores) / len(baseline_scores))
            )
        if effects:
            variant_effects[variant_id] = effects

    if len(variant_effects) < 2:
        raise ContractError("prompt interaction requires at least two paired prompt variants")

    observed_means = [sum(effects) / len(effects) for effects in variant_effects.values()]
    observed_spread = max(observed_means) - min(observed_means)

    rng = random.Random(seed)
    extreme_count = 0
    for _ in range(num_permutations):
        permuted_means = []
        for effects in variant_effects.values():
            permuted = [effect if rng.randrange(2) else -effect for effect in effects]
            permuted_means.append(sum(permuted) / len(permuted))
        permuted_spread = max(permuted_means) - min(permuted_means)
        if permuted_spread >= observed_spread - 1e-12:
            extreme_count += 1

    p_value = (extreme_count + 1) / (num_permutations + 1)
    return InteractionResult(blocks_claim=p_value < alpha, p_value=p_value)


def confirmation_decision(
    effect: EffectEstimate,
    defects: RiskRatioEstimate,
    economics: EffectEstimate,
    censoring: CensoringReport,
    interaction: InteractionResult,
    analyzed_runs: int,
    required_runs: int,
) -> Decision:
    """Evaluate 7 confirmatory decision criteria."""
    reasons = []

    if effect.low <= 0.0:
        reasons.append("quality confidence interval includes zero or negative values")

    if effect.point < 0.05:
        reasons.append(f"quality point estimate ({effect.point:.3f}) below 0.05 threshold")

    if defects.high >= 1.10:
        reasons.append(f"severe defect risk ratio upper bound ({defects.high:.2f}) >= 1.10")

    if economics.low <= 0.0:
        reasons.append("economic net value lower confidence bound is not positive")

    if censoring.requires_protocol_review:
        reasons.append("censoring rate exceeds 10% protocol review threshold")

    if interaction.blocks_claim:
        reasons.append("material prompt interaction blocks broad condition claim")

    if analyzed_runs < required_runs:
        reasons.append(f"underpowered sample size ({analyzed_runs} < {required_runs})")

    adopt = len(reasons) == 0
    return Decision(adopt=adopt, reasons=reasons)
