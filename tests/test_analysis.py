"""Effect estimates, Holm-Bonferroni correction, and confirmation decisions tests (RED phase)."""

import pytest

from tdd_ablation.analysis import (
    AnalysisRow,
    CostModel,
    Decision,
    EffectEstimate,
    InteractionResult,
    RiskRatioEstimate,
    confirmation_decision,
    holm_bonferroni_adjust,
    paired_effect,
    prompt_interaction,
)
from tdd_ablation.budget import CensoringReport

STRONG_EFFECT = EffectEstimate(point=0.08, low=0.06, high=0.10)
SAFE_DEFECTS = RiskRatioEstimate(point=0.85, low=0.70, high=1.05)
POSITIVE_ECONOMICS = EffectEstimate(point=150.0, low=20.0, high=280.0)
ACCEPTABLE_CENSORING = CensoringReport(total=144, censored=5, rate_by_condition={"5": 0.03}, requires_protocol_review=False)
NO_BLOCKING_INTERACTION = InteractionResult(blocks_claim=False, p_value=0.45)
BLOCKING_INTERACTION = InteractionResult(blocks_claim=True, p_value=0.01)


def test_cost_model_calculates_net_expected_value():
    cost_model = CostModel(
        token_price_per_k=0.003,
        review_cost_per_min=1.50,
        defect_cost_by_severity={"low": 50, "medium": 200, "high": 1000, "critical": 5000},
        delay_cost_per_hour=100.0,
    )
    # 5 avoided high defects (5000) - 100k tokens (0.30) - 30 min review (45.0) - 0.5 hr delay (50.0)
    net_val = cost_model.calculate_net_value(
        avoided_defects={"high": 5},
        tokens_used=100_000,
        review_minutes=30.0,
        delay_hours=0.5,
    )
    assert net_val == (5000.0 - 0.30 - 45.0 - 50.0)


def test_holm_bonferroni_adjust_controls_fwer():
    p_vals = [0.005, 0.01, 0.03, 0.04, 0.10, 0.20, 0.50, 0.80]
    results = holm_bonferroni_adjust(p_vals, alpha=0.05)
    # Sorted order:
    # k=1 (0.005 vs 0.05/8=0.00625) -> True
    # k=2 (0.01 vs 0.05/7=0.00714) -> False -> all subsequent False
    assert results[0] is True
    assert results[1] is False
    assert sum(results) == 1


def test_confirmation_requires_all_seven_criteria():
    decision = confirmation_decision(
        effect=STRONG_EFFECT,
        defects=SAFE_DEFECTS,
        economics=POSITIVE_ECONOMICS,
        censoring=ACCEPTABLE_CENSORING,
        interaction=NO_BLOCKING_INTERACTION,
        analyzed_runs=144,
        required_runs=144,
    )
    assert decision.adopt is True


def test_blocking_prompt_interaction_forces_rejection():
    decision = confirmation_decision(
        effect=STRONG_EFFECT,
        defects=SAFE_DEFECTS,
        economics=POSITIVE_ECONOMICS,
        censoring=ACCEPTABLE_CENSORING,
        interaction=BLOCKING_INTERACTION,
        analyzed_runs=144,
        required_runs=144,
    )
    assert decision.adopt is False
    assert "prompt interaction" in decision.reasons[0]
