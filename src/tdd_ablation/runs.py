"""Immutable run artifact import and verification."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from tdd_ablation.contracts import ContractError, load_json, require_fields
from tdd_ablation.hashing import hash_tree
from tdd_ablation.schedule import ScheduleRow


@dataclass(frozen=True)
class DuplicateAttestation:
    reviewer_ids: list[str]
    evidence_paths: list[str]
    rationale: str


@dataclass(frozen=True)
class ImportedRunRecord:
    run_id: str
    phase: str
    order: int
    task_id: str
    condition_id: str
    baseline_condition_id: str | None
    variant_id: str
    repetition: int
    seed: int
    artifact_hash: str
    tokens_used: int
    duration_seconds: float
    duplicate_of: str | None = None
    attestation: DuplicateAttestation | None = None


def import_run(
    schedule_row: ScheduleRow,
    source: Path,
    metadata: dict[str, Any],
    store: Path,
    duplicate_attestation: DuplicateAttestation | None = None,
) -> ImportedRunRecord:
    """Import run artifacts into store as immutable directory."""
    if not source.exists() or not source.is_dir():
        raise ContractError(f"source path must be an existing directory: {source}")

    require_fields(metadata, {"tokens_used", "duration_seconds"}, "run_metadata")

    run_id = schedule_row.run_id
    run_dir = store / run_id
    if run_dir.exists():
        raise ContractError(f"run_id {run_id!r} already imported in store")

    art_hash = hash_tree(source)

    # Check store for duplicate artifact hash
    duplicate_of: str | None = None
    store.mkdir(parents=True, exist_ok=True)
    for existing_manifest in store.glob("*/manifest.json"):
        try:
            ex_data = load_json(existing_manifest)
            if ex_data.get("artifact_hash") == art_hash:
                duplicate_of = ex_data.get("run_id")
                break
        except ContractError:
            continue

    if duplicate_of and not duplicate_attestation:
        raise ContractError(
            f"duplicate artifact hash {art_hash!r} matches existing run {duplicate_of!r}. "
            f"Attestation required."
        )

    # Copy files to temporary folder first, then write manifest and atomic rename
    tmp_run_dir = store / f".tmp-{run_id}"
    if tmp_run_dir.exists():
        shutil.rmtree(tmp_run_dir)

    art_dst = tmp_run_dir / "artifacts"
    shutil.copytree(source, art_dst)

    record = ImportedRunRecord(
        run_id=run_id,
        phase=schedule_row.phase,
        order=schedule_row.order,
        task_id=schedule_row.task_id,
        condition_id=schedule_row.condition_id,
        baseline_condition_id=schedule_row.baseline_condition_id,
        variant_id=schedule_row.variant_id,
        repetition=schedule_row.repetition,
        seed=schedule_row.seed,
        artifact_hash=art_hash,
        tokens_used=int(metadata["tokens_used"]),
        duration_seconds=float(metadata["duration_seconds"]),
        duplicate_of=duplicate_of,
        attestation=duplicate_attestation,
    )

    manifest_path = tmp_run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")

    tmp_run_dir.rename(run_dir)
    return record


def verify_store(store: Path) -> list[str]:
    """Verify integrity of all imported runs in store. Returns list of corrupted run_ids."""
    if not store.exists():
        return []

    corrupted: list[str] = []

    for run_dir in sorted(store.iterdir()):
        if not run_dir.is_dir() or run_dir.name.startswith("."):
            continue

        manifest_path = run_dir / "manifest.json"
        art_dir = run_dir / "artifacts"

        if not manifest_path.exists() or not art_dir.exists():
            corrupted.append(run_dir.name)
            continue

        try:
            meta = load_json(manifest_path)
            expected_hash = meta.get("artifact_hash")
            actual_hash = hash_tree(art_dir)
            if actual_hash != expected_hash:
                corrupted.append(run_dir.name)
        except Exception:
            corrupted.append(run_dir.name)

    return corrupted
