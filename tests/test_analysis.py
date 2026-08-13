"""Effect estimates, Holm-Bonferroni correction, and confirmation decisions tests."""

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
from tdd_ablation.contracts import ContractError

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
    net_val = cost_model.calculate_net_value(
        avoided_defects={"high": 5},
        tokens_used=100_000,
        review_minutes=30.0,
        delay_hours=0.5,
    )
    assert net_val == (5000.0 - 0.30 - 45.0 - 50.0)


def test_holm_bonferroni_adjust_controls_fwer():
    assert holm_bonferroni_adjust([]) == []

    p_vals = [0.005, 0.01, 0.03, 0.04, 0.10, 0.20, 0.50, 0.80]
    results = holm_bonferroni_adjust(p_vals, alpha=0.05)
    assert results[0] is True
    assert results[1] is False
    assert sum(results) == 1


def test_paired_effect_bootstrap_calculation():
    rows = [
        AnalysisRow(task_id="t1", condition_id="1", variant_id="v1", score=0.70, high_severity_defects=0),
        AnalysisRow(task_id="t1", condition_id="2", variant_id="v1", score=0.85, high_severity_defects=0),
        AnalysisRow(task_id="t2", condition_id="1", variant_id="v1", score=0.60, high_severity_defects=1),
        AnalysisRow(task_id="t2", condition_id="2", variant_id="v1", score=0.75, high_severity_defects=0),
    ]
    eff = paired_effect(rows, baseline="1", treatment="2", seed=42, num_bootstraps=50)
    assert eff.point == pytest.approx(0.15)
    assert eff.low <= eff.point <= eff.high


def test_paired_effect_missing_scores_raises_error():
    rows = [
        AnalysisRow(task_id="t1", condition_id="1", variant_id="v1", score=0.70, high_severity_defects=0),
    ]
    with pytest.raises(ContractError, match="missing scores"):
        paired_effect(rows, baseline="1", treatment="2", seed=42)


def test_paired_effect_preserves_repeated_sampled_clusters():
    rows = []
    for task_id, treatment_score in enumerate([0.0, 0.0, 0.0, 0.0, 100.0], start=1):
        rows.extend(
            [
                AnalysisRow(str(task_id), "baseline", "v1", 0.0, 0),
                AnalysisRow(str(task_id), "treatment", "v1", treatment_score, 0),
            ]
        )

    effect = paired_effect(
        rows,
        baseline="baseline",
        treatment="treatment",
        seed=7,
        num_bootstraps=500,
    )

    assert effect.point == 20.0
    assert effect.low == 0.0
    assert effect.high == 60.0


def test_paired_effect_rejects_task_missing_treatment_pair():
    rows = [
        AnalysisRow("complete", "baseline", "v1", 0.2, 0),
        AnalysisRow("complete", "treatment", "v1", 0.4, 0),
        AnalysisRow("incomplete", "baseline", "v1", 0.3, 0),
    ]

    with pytest.raises(ContractError, match="missing paired scores for task incomplete"):
        paired_effect(rows, baseline="baseline", treatment="treatment", seed=7)


def test_prompt_interaction_does_not_block_equal_variant_effects():
    rows = []
    for task_id in ["t1", "t2", "t3", "t4"]:
        for variant_id in ["v1", "v2"]:
            rows.extend(
                [
                    AnalysisRow(task_id, "baseline", variant_id, 0.5, 0),
                    AnalysisRow(task_id, "treatment", variant_id, 0.7, 0),
                ]
            )

    res = prompt_interaction(
        rows,
        baseline="baseline",
        treatment="treatment",
        seed=11,
        num_permutations=499,
    )

    assert res.blocks_claim is False
    assert res.p_value == 1.0


def test_prompt_interaction_blocks_opposing_variant_effects():
    rows = []
    for task_number in range(1, 9):
        task_id = f"t{task_number}"
        rows.extend(
            [
                AnalysisRow(task_id, "baseline", "v1", 0.0, 0),
                AnalysisRow(task_id, "treatment", "v1", 1.0, 0),
                AnalysisRow(task_id, "baseline", "v2", 1.0, 0),
                AnalysisRow(task_id, "treatment", "v2", 0.0, 0),
            ]
        )

    res = prompt_interaction(
        rows,
        baseline="baseline",
        treatment="treatment",
        seed=11,
        num_permutations=999,
    )

    assert res.blocks_claim is True
    assert res.p_value < 0.05


def test_prompt_interaction_requires_two_paired_variants():
    rows = [
        AnalysisRow("t1", "baseline", "v1", 0.0, 0),
        AnalysisRow("t1", "treatment", "v1", 1.0, 0),
    ]

    with pytest.raises(ContractError, match="at least two paired prompt variants"):
        prompt_interaction(rows, baseline="baseline", treatment="treatment")


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


def test_confirmation_rejection_reasons():
    weak_effect = EffectEstimate(point=0.03, low=-0.01, high=0.07)
    bad_defects = RiskRatioEstimate(point=1.20, low=1.05, high=1.35)
    bad_econ = EffectEstimate(point=-50.0, low=-100.0, high=10.0)
    high_censoring = CensoringReport(total=144, censored=20, rate_by_condition={"5": 0.15}, requires_protocol_review=True)

    decision = confirmation_decision(
        effect=weak_effect,
        defects=bad_defects,
        economics=bad_econ,
        censoring=high_censoring,
        interaction=BLOCKING_INTERACTION,
        analyzed_runs=100,
        required_runs=144,
    )
    assert decision.adopt is False
    assert len(decision.reasons) == 7
