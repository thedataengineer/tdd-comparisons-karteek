"""Budget pilot and censoring rules tests (RED phase)."""

from dataclasses import dataclass

import pytest

from tdd_ablation.budget import (
    BudgetDecision,
    CensoringReport,
    PilotRun,
    RunRecord,
    budget_decision,
    censoring_report,
    shared_token_ceiling,
    shared_timeout,
)
from tdd_ablation.contracts import ContractError

CONDITIONS = ["1", "2", "3", "4", "5", "6a", "6b", "6c"]


def make_pilot_runs(count_per_cond: int = 12, max_tokens: int = 100_000, max_time: int = 3_000):
    runs = []
    for cond in CONDITIONS:
        for i in range(count_per_cond):
            tokens = 50_000 if i < count_per_cond - 1 else max_tokens
            time_sec = 1_000 if i < count_per_cond - 1 else max_time
            runs.append(
                PilotRun(
                    condition_id=cond,
                    tokens_used=tokens,
                    duration_seconds=time_sec,
                    excluded_from_analysis=True,
                )
            )
    return runs


def test_shared_ceiling_uses_largest_condition_max_plus_margin():
    pilots = make_pilot_runs(12, max_tokens=100_000)
    ceiling = shared_token_ceiling(pilots, provider_limit=200_000)
    assert ceiling == 120_000  # 100_000 * 1.20


def test_shared_timeout_uses_largest_condition_max_plus_margin_and_cap():
    pilots = make_pilot_runs(12, max_time=3_000)
    assert shared_timeout(pilots, runtime_cap_seconds=7_200) == 3_600  # 3_000 * 1.20
    assert shared_timeout(pilots, runtime_cap_seconds=3_000) == 3_000  # capped


def test_ceiling_rejects_fewer_than_twelve_pilot_runs_per_condition():
    thin_pilots = make_pilot_runs(5)
    with pytest.raises(ContractError, match="12 pilot runs"):
        shared_token_ceiling(thin_pilots, provider_limit=200_000)


def test_protocol_review_triggers_above_ten_percent():
    runs = [
        RunRecord(run_id=f"r-{i}", condition_id="5", exit_status="token_exhausted")
        if i < 3
        else RunRecord(run_id=f"r-{i}", condition_id="5", exit_status="success")
        for i in range(20)
    ]
    report = censoring_report(runs)
    assert report.requires_protocol_review is True


def test_budget_decision_serializes_all_inputs_and_outputs():
    pilots = make_pilot_runs(12, max_tokens=100_000, max_time=3_000)
    decision = budget_decision(pilots, provider_limit=200_000, runtime_cap_seconds=7_200)
    assert decision.token_ceiling == 120_000
    assert decision.timeout_seconds == 3_600
    assert decision.provider_limit == 200_000
    assert decision.runtime_cap_seconds == 7_200
    assert decision.samples_per_condition == {c: 12 for c in CONDITIONS}
