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
    source = tmp_path / "run_store" / sample_imported_run.run_id / "artifacts"
    packet = prepare_blind_review(sample_imported_run, dest, source)
    manifest = json.loads(packet.manifest_path.read_text())
    assert set(manifest.keys()) <= REVIEW_MANIFEST_ALLOWLIST


def test_packet_id_is_neutral_alias_not_run_id(sample_imported_run: ImportedRunRecord, tmp_path: Path):
    dest = tmp_path / "packets"
    source = tmp_path / "run_store" / sample_imported_run.run_id / "artifacts"
    packet = prepare_blind_review(sample_imported_run, dest, source)
    assert sample_imported_run.run_id not in packet.manifest_path.read_text()
    assert sample_imported_run.run_id not in str(packet.artifact_path)


def test_review_packet_copies_source_and_excludes_trace(
    sample_imported_run: ImportedRunRecord, tmp_path: Path
):
    source = tmp_path / "run_store" / sample_imported_run.run_id / "artifacts"
    package = source / "package"
    package.mkdir()
    (package / "helper.py").write_text("VALUE = 42\n", encoding="utf-8")
    (source / "prompt.txt").write_text("condition 6a secret prompt\n", encoding="utf-8")
    (source / "manifest.json").write_text('{"condition_id": "6a"}\n', encoding="utf-8")
    (source / "metadata.json").write_text('{"run_id": "scr-17-0001"}\n', encoding="utf-8")

    packet = prepare_blind_review(sample_imported_run, tmp_path / "packets", source)
    manifest = json.loads(packet.manifest_path.read_text(encoding="utf-8"))

    assert (packet.artifact_path / "solution.py").read_text(encoding="utf-8") == "def solve(): pass\n"
    assert (packet.artifact_path / "package" / "helper.py").read_text(encoding="utf-8") == "VALUE = 42\n"
    assert not (packet.artifact_path / "trace.log").exists()
    assert not (packet.artifact_path / "prompt.txt").exists()
    assert not (packet.artifact_path / "manifest.json").exists()
    assert not (packet.artifact_path / "metadata.json").exists()
    assert manifest["artifact_files"] == ["package/helper.py", "solution.py"]


def test_review_packet_rejects_missing_artifact_source(
    sample_imported_run: ImportedRunRecord, tmp_path: Path
):
    with pytest.raises(ContractError, match="artifact source must be an existing directory"):
        prepare_blind_review(sample_imported_run, tmp_path / "packets", tmp_path / "missing")


def test_review_packet_rejects_symlinks(sample_imported_run: ImportedRunRecord, tmp_path: Path):
    source = tmp_path / "run_store" / sample_imported_run.run_id / "artifacts"
    (source / "linked.py").symlink_to(source / "solution.py")

    with pytest.raises(ContractError, match="symlinks not allowed"):
        prepare_blind_review(sample_imported_run, tmp_path / "packets", source)


def test_review_packet_rerun_removes_stale_artifacts(
    sample_imported_run: ImportedRunRecord, tmp_path: Path
):
    source = tmp_path / "run_store" / sample_imported_run.run_id / "artifacts"
    obsolete = source / "obsolete.py"
    obsolete.write_text("SECRET = True\n", encoding="utf-8")
    destination = tmp_path / "packets"

    first_packet = prepare_blind_review(sample_imported_run, destination, source)
    assert (first_packet.artifact_path / "obsolete.py").exists()

    obsolete.unlink()
    second_packet = prepare_blind_review(sample_imported_run, destination, source)

    assert not (second_packet.artifact_path / "obsolete.py").exists()


def test_low_reliability_requires_full_rescore():
    with pytest.raises(ContractError, match="full independent rescoring"):
        validate_review_panel(ReliabilityResult(metric="weighted_kappa", value=0.62))
