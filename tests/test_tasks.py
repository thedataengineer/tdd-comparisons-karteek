"""Task manifests and severity calibration reliability tests."""

from pathlib import Path

import pytest

from tdd_ablation.contracts import ContractError, load_json
from tdd_ablation.reliability import (
    validate_severity_calibration,
    weighted_kappa,
)
from tdd_ablation.tasks import validate_task_manifest


def test_weighted_kappa_perfect_agreement():
    left = [0, 1, 2, 3, 0, 1, 2, 3]
    right = [0, 1, 2, 3, 0, 1, 2, 3]
    assert weighted_kappa(left, right) == pytest.approx(1.0)


def test_weighted_kappa_disagreement():
    left = [0, 0, 0, 0, 3, 3, 3, 3]
    right = [3, 3, 3, 3, 0, 0, 0, 0]
    assert weighted_kappa(left, right) < 0.0


def test_severity_calibration_requires_point_eight_agreement():
    ratings = {
        "reviewer_a": [0, 1, 2, 3, 0, 1, 2, 3, 0, 1],
        "reviewer_b": [3, 2, 1, 0, 3, 2, 1, 0, 3, 2],
    }
    with pytest.raises(ContractError, match="below 0.80"):
        validate_severity_calibration(ratings)


def test_severity_calibration_passes_high_agreement():
    ratings = {
        "reviewer_a": [0, 1, 2, 3, 0, 1, 2, 3, 0, 1],
        "reviewer_b": [0, 1, 2, 3, 0, 1, 2, 3, 0, 1],
    }
    kappa = validate_severity_calibration(ratings)
    assert kappa >= 0.80


def test_task_requires_frozen_hidden_test_mapping():
    data = load_json(Path("study/tasks/task.example.json"))
    del data["hidden_tests"]
    with pytest.raises(ContractError, match="hidden_tests"):
        validate_task_manifest(data, draft=False)


def test_task_draft_manifest_allows_missing_hidden_tests():
    data = load_json(Path("study/tasks/task.example.json"))
    del data["hidden_tests"]
    validate_task_manifest(data, draft=True)


def test_task_manifest_invalid_family():
    data = load_json(Path("study/tasks/task.example.json"))
    data["family"] = "invalid_family"
    with pytest.raises(ContractError, match="invalid family"):
        validate_task_manifest(data)


def test_task_manifest_invalid_resource_limits():
    data = load_json(Path("study/tasks/task.example.json"))
    data["resource_limits"] = "not_a_dict"
    with pytest.raises(ContractError, match="resource_limits must be a dict"):
        validate_task_manifest(data)


def test_task_manifest_invalid_hidden_tests():
    data = load_json(Path("study/tasks/task.example.json"))
    data["hidden_tests"] = {}
    with pytest.raises(ContractError, match="cannot be empty"):
        validate_task_manifest(data)

    data["hidden_tests"] = {"test1": "not_a_dict"}
    with pytest.raises(ContractError, match="must be a dict"):
        validate_task_manifest(data)

    data["hidden_tests"] = {"test1": {"business_behavior": "test", "severity": "invalid_severity"}}
    with pytest.raises(ContractError, match="invalid severity"):
        validate_task_manifest(data)
