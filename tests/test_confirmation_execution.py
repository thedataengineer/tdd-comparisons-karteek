"""Confirmation execution and publication tests (RED phase)."""

from pathlib import Path

from tdd_ablation.contracts import load_json


def test_confirmation_artifacts_and_final_reports_exist():
    cnf_sch = Path("study/confirmation/schedule.csv")
    final_report = Path("study/reports/final.md")
    repro_json = Path("study/reports/reproduction.json")

    assert cnf_sch.exists()
    assert final_report.exists()
    assert repro_json.exists()

    repro = load_json(repro_json)
    assert repro["run_one_hash"] == repro["run_two_hash"]
    assert repro["reproducible"] is True
