"""Blind review reliability tests (RED phase)."""

import json
from pathlib import Path

import pytest

from tdd_ablation.contracts import ContractError
from tdd_ablation.reliability import ReliabilityResult, validate_review_panel
from tdd_ablation.reviews import prepare_blind_review, review_reliability
from tdd_ablation.runs import ImportedRunRecord

REVIEW_MANIFEST_ALLOWLIST = {
    "packet_id",
    "task_id",
    "artifact_files",
    "rubric_version",
    "language",
    "entry_point",
}


@pytest.fixture
def sample_imported_run(tmp_path: Path) -> ImportedRunRecord:
    run_dir = tmp_path / "run_store" / "scr-17-0001"
    art_dir = run_dir / "artifacts"
    art_dir.mkdir(parents=True)
    (art_dir / "solution.py").write_text("def solve(): pass\n")
    (art_dir / "trace.log").write_text("secret trace data with condition 6a\n")

    manifest = {
        "run_id": "scr-17-0001",
        "phase": "screening",
        "order": 1,
        "task_id": "task-01",
        "condition_id": "6a",
        "baseline_condition_id": None,
        "variant_id": "v1",
        "repetition": 1,
        "seed": 17,
        "artifact_hash": "dummy_hash",
        "tokens_used": 100,
        "duration_seconds": 2.0,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest))

    return ImportedRunRecord(
        run_id="scr-17-0001",
        phase="screening",
        order=1,
        task_id="task-01",
        condition_id="6a",
        baseline_condition_id=None,
        variant_id="v1",
        repetition=1,
        seed=17,
        artifact_hash="dummy_hash",
        tokens_used=100,
        duration_seconds=2.0,
    )


def test_review_manifest_contains_only_allowlisted_keys(sample_imported_run: ImportedRunRecord, tmp_path: Path):
    dest = tmp_path / "packets"
    packet = prepare_blind_review(sample_imported_run, dest)
    manifest = json.loads(packet.manifest_path.read_text())
    assert set(manifest.keys()) <= REVIEW_MANIFEST_ALLOWLIST


def test_packet_id_is_neutral_alias_not_run_id(sample_imported_run: ImportedRunRecord, tmp_path: Path):
    dest = tmp_path / "packets"
    packet = prepare_blind_review(sample_imported_run, dest)
    assert sample_imported_run.run_id not in packet.manifest_path.read_text()
    assert sample_imported_run.run_id not in str(packet.artifact_path)


def test_low_reliability_requires_full_rescore():
    with pytest.raises(ContractError, match="full independent rescoring"):
        validate_review_panel(ReliabilityResult(metric="weighted_kappa", value=0.62))
