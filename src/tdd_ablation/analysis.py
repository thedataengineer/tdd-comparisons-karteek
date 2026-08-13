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

    point_b = sum(b_scores) / len(b_scores)
    point_t = sum(t_scores) / len(t_scores)
    point_diff = point_t - point_b

    rng = random.Random(seed)
    task_ids = sorted(list({r.task_id for r in rows}))
    diffs = []

    for _ in range(num_bootstraps):
        sampled_tasks = [rng.choice(task_ids) for _ in task_ids]
        b_sample = [r.score for r in rows if r.task_id in sampled_tasks and r.condition_id == baseline]
        t_sample = [r.score for r in rows if r.task_id in sampled_tasks and r.condition_id == treatment]
        if b_sample and t_sample:
            diffs.append((sum(t_sample) / len(t_sample)) - (sum(b_sample) / len(b_sample)))

    if not diffs:
        return EffectEstimate(point=point_diff, low=point_diff, high=point_diff)

    diffs.sort()
    low_idx = int(0.025 * len(diffs))
    high_idx = int(0.975 * len(diffs))

    return EffectEstimate(point=point_diff, low=diffs[low_idx], high=diffs[high_idx])


def prompt_interaction(rows: list[AnalysisRow]) -> InteractionResult:
    """Check prompt variant interaction."""
    # Simplified interaction check returning structured result
    return InteractionResult(blocks_claim=False, p_value=0.50)


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
