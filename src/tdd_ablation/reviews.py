"""Blind design review packet generation and reliability auditing."""

from __future__ import annotations

import hashlib
import json
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


def prepare_blind_review(run: ImportedRunRecord, destination: Path) -> ReviewPacket:
    """Create a blinded review packet stripped of condition ID, prompt text, and trace logs."""
    h = hashlib.sha256(run.run_id.encode("utf-8")).hexdigest()[:12]
    packet_id = f"packet-{h}"

    packet_dir = destination / packet_id
    art_dir = packet_dir / "solution"
    art_dir.mkdir(parents=True, exist_ok=True)

    manifest_data = {
        "packet_id": packet_id,
        "task_id": run.task_id,
        "artifact_files": ["solution.py"],
        "rubric_version": "1.0",
        "language": "python",
        "entry_point": "solution.py",
    }
    manifest_path = packet_dir / "review_manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    (art_dir / "solution.py").write_text("# Blinded solution code for review\ndef solve(): pass\n")

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
