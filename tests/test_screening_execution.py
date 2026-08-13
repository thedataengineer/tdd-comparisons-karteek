"""Screening execution and auditing tests (RED phase)."""

from pathlib import Path

from tdd_ablation.contracts import load_json


def test_screening_execution_artifacts_exist():
    sch_path = Path("study/screening/schedule.csv")
    audit_path = Path("study/screening/audit.json")

    assert sch_path.exists()
    assert audit_path.exists()

    audit = load_json(audit_path)
    assert audit["total_screening_runs"] == 576
    assert audit["censoring_rate"] <= 0.10
    assert audit["store_integrity_verified"] is True
