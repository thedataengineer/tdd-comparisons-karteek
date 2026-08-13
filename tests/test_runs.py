"""Immutable run import tests (RED phase)."""

import json
from pathlib import Path

import pytest

from tdd_ablation.contracts import ContractError
from tdd_ablation.hashing import hash_tree
from tdd_ablation.runs import DuplicateAttestation, import_run, verify_store
from tdd_ablation.schedule import ScheduleRow

ROW_A = ScheduleRow(
    run_id="scr-17-0001",
    phase="screening",
    order=1,
    task_id="task-01",
    condition_id="1",
    baseline_condition_id=None,
    variant_id="v1",
    repetition=1,
    seed=17,
)

ROW_B = ScheduleRow(
    run_id="scr-17-0002",
    phase="screening",
    order=2,
    task_id="task-01",
    condition_id="2",
    baseline_condition_id=None,
    variant_id="v1",
    repetition=1,
    seed=17,
)

ATTESTATION = DuplicateAttestation(
    reviewer_ids=["rev_1", "rev_2"],
    evidence_paths=["obs1.log", "obs2.log"],
    rationale="Independent identical solution generated.",
)


@pytest.fixture
def source_dir(tmp_path: Path) -> Path:
    src = tmp_path / "source_run"
    src.mkdir()
    (src / "solution.py").write_text("def solve(): return 42\n")
    return src


def test_hash_tree_is_deterministic(source_dir: Path):
    h1 = hash_tree(source_dir)
    h2 = hash_tree(source_dir)
    assert h1 == h2
    assert len(h1) == 64


def test_import_rejects_duplicate_artifact_without_attestation(source_dir: Path, tmp_path: Path):
    store = tmp_path / "store"
    meta = {"tokens_used": 100, "duration_seconds": 5.0}
    first = import_run(ROW_A, source_dir, meta, store)
    assert first.run_id == ROW_A.run_id

    with pytest.raises(ContractError, match="duplicate artifact hash"):
        import_run(ROW_B, source_dir, meta, store)


def test_attested_duplicate_imports_and_is_flagged(source_dir: Path, tmp_path: Path):
    store = tmp_path / "store"
    meta = {"tokens_used": 100, "duration_seconds": 5.0}
    import_run(ROW_A, source_dir, meta, store)
    record = import_run(ROW_B, source_dir, meta, store, duplicate_attestation=ATTESTATION)
    assert record.duplicate_of == ROW_A.run_id
    assert record.attestation == ATTESTATION


def test_verify_store_detects_changed_file(source_dir: Path, tmp_path: Path):
    store = tmp_path / "store"
    meta = {"tokens_used": 100, "duration_seconds": 5.0}
    record = import_run(ROW_A, source_dir, meta, store)
    run_path = store / record.run_id
    (run_path / "artifacts" / "solution.py").write_text("modified code")
    corrupted = verify_store(store)
    assert corrupted == [record.run_id]
