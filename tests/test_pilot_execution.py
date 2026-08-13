"""Budget pilot execution tests (RED phase)."""

from pathlib import Path

from tdd_ablation.contracts import load_json


def test_pilot_schedule_and_decision_exist():
    sch_path = Path("study/pilot/schedule.csv")
    dec_path = Path("study/pilot/budget-decision.json")

    assert sch_path.exists()
    assert dec_path.exists()

    decision = load_json(dec_path)
    assert decision["token_ceiling"] > 0
    assert decision["timeout_seconds"] > 0
    assert decision["provider_limit"] == 200_000
    assert decision["runtime_cap_seconds"] == 7_200
