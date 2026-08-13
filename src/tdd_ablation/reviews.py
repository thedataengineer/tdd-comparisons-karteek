"""Blind design review packet generation and reliability auditing."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tdd_ablation.contracts import ContractError
from tdd_ablation.reliability import ReliabilityResult, weighted_kappa
from tdd_ablation.runs import ImportedRunRecord


@dataclass(frozen=True)
class ReviewPacket:
    packet_id: str
    manifest_path: Path
    artifact_path: Path


_TRACE_FILENAMES = {"trace.json", "trace.log", "execution-trace.json", "execution_trace.json"}
_TRACE_SUFFIXES = {".log"}
_SENSITIVE_PREFIXES = (
    "condition.",
    "condition_",
    "execution-metadata",
    "execution_metadata",
    "manifest.",
    "manifest_",
    "metadata.",
    "metadata_",
    "prompt.",
    "prompt_",
    "run-metadata",
    "run_metadata",
    "trace.",
    "trace_",
)
_SENSITIVE_DIRECTORIES = {"metadata", "prompts", "traces"}


def prepare_blind_review(
    run: ImportedRunRecord,
    destination: Path,
    artifact_source: Path,
) -> ReviewPacket:
    """Create a blinded review packet stripped of condition ID, prompt text, and trace logs."""
    if not artifact_source.is_dir():
        raise ContractError(f"artifact source must be an existing directory: {artifact_source}")

    source_files: list[tuple[str, Path]] = []
    for source_path in artifact_source.rglob("*"):
        if source_path.is_symlink():
            raise ContractError(f"symlinks not allowed in review artifacts: {source_path}")
        if not source_path.is_file():
            continue
        relative = source_path.relative_to(artifact_source)
        relative_path = relative.as_posix()
        lower_name = source_path.name.lower()
        lower_directories = {part.lower() for part in relative.parts[:-1]}
        if (
            lower_name in _TRACE_FILENAMES
            or source_path.suffix.lower() in _TRACE_SUFFIXES
            or lower_name.startswith(_SENSITIVE_PREFIXES)
            or lower_directories & _SENSITIVE_DIRECTORIES
        ):
            continue
        source_files.append((relative_path, source_path))

    source_files.sort(key=lambda item: item[0])
    if not source_files:
        raise ContractError(f"artifact source contains no reviewable files: {artifact_source}")

    h = hashlib.sha256(run.run_id.encode("utf-8")).hexdigest()[:12]
    packet_id = f"packet-{h}"

    packet_dir = destination / packet_id
    if packet_dir.is_symlink():
        raise ContractError(f"review packet path must not be a symlink: {packet_dir}")
    if packet_dir.exists():
        shutil.rmtree(packet_dir)
    art_dir = packet_dir / "solution"
    art_dir.mkdir(parents=True, exist_ok=True)

    artifact_files = [relative_path for relative_path, _ in source_files]
    entry_point = "solution.py" if "solution.py" in artifact_files else artifact_files[0]
    manifest_data = {
        "packet_id": packet_id,
        "task_id": run.task_id,
        "artifact_files": artifact_files,
        "rubric_version": "1.0",
        "language": "python",
        "entry_point": entry_point,
    }
    manifest_path = packet_dir / "review_manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    for relative_path, source_path in source_files:
        destination_path = art_dir / relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)

    return ReviewPacket(
        packet_id=packet_id,
        manifest_path=manifest_path,
        artifact_path=art_dir,
    )


def review_reliability(reviews: list[dict[str, Any]]) -> ReliabilityResult:
    """Calculate inter-rater agreement across blind review scores."""
    if not reviews or len(reviews) < 2:
        raise ContractError("review_reliability requires at least two review records")

    r1_scores = [r["reviewer_1_score"] for r in reviews]
    r2_scores = [r["reviewer_2_score"] for r in reviews]

    val = weighted_kappa(r1_scores, r2_scores)
    return ReliabilityResult(metric="weighted_kappa", value=val)
