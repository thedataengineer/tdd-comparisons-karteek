"""Task manifests and severity calibration reliability tests (RED phase)."""

from pathlib import Path

import pytest

from tdd_ablation.contracts import ContractError, load_json
from tdd_ablation.reliability import (
    validate_severity_calibration,
    weighted_kappa,
)
from tdd_ablation.tasks import validate_task_manifest


# --- reliability tests ---

def test_weighted_kappa_perfect_agreement():
    """Perfect agreement gives kappa = 1.0."""
    left = [0, 1, 2, 3, 0, 1, 2, 3]
    right = [0, 1, 2, 3, 0, 1, 2, 3]
    assert weighted_kappa(left, right) == pytest.approx(1.0)


def test_weighted_kappa_disagreement():
    """Disagreement reduces kappa."""
    left = [0, 0, 0, 0, 3, 3, 3, 3]
    right = [3, 3, 3, 3, 0, 0, 0, 0]
    assert weighted_kappa(left, right) < 0.0


def test_severity_calibration_requires_point_eight_agreement():
    """Weighted kappa < 0.80 raises ContractError."""
    ratings = {
        "reviewer_a": [0, 1, 2, 3, 0, 1, 2, 3, 0, 1],
        "reviewer_b": [3, 2, 1, 0, 3, 2, 1, 0, 3, 2],
    }
    with pytest.raises(ContractError, match="below 0.80"):
        validate_severity_calibration(ratings)


def test_severity_calibration_passes_high_agreement():
    """Kappa >= 0.80 passes and returns kappa value."""
    ratings = {
        "reviewer_a": [0, 1, 2, 3, 0, 1, 2, 3, 0, 1],
        "reviewer_b": [0, 1, 2, 3, 0, 1, 2, 3, 0, 1],
    }
    kappa = validate_severity_calibration(ratings)
    assert kappa >= 0.80


# --- tasks tests ---

def test_task_requires_frozen_hidden_test_mapping():
    """Task manifest missing hidden_tests fails non-draft validation."""
    data = load_json(Path("study/tasks/task.example.json"))
    del data["hidden_tests"]
    with pytest.raises(ContractError, match="hidden_tests"):
        validate_task_manifest(data, draft=False)


def test_task_draft_manifest_allows_missing_hidden_tests():
    """Draft task manifest allows missing hidden_tests when draft=True."""
    data = load_json(Path("study/tasks/task.example.json"))
    del data["hidden_tests"]
    validate_task_manifest(data, draft=True)
