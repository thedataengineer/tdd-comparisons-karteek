"""Contract module tests — written before contracts.py exists (RED phase)."""

import json
from pathlib import Path

import pytest

from tdd_ablation.contracts import (
    ContractError,
    load_json,
    require_fields,
    validate_identifier,
)


# --- require_fields ---


def test_require_fields_reports_missing_names():
    """Missing fields are named in the error, sorted for determinism."""
    with pytest.raises(ContractError, match="run: missing fields: condition_id, task_id"):
        require_fields({}, {"task_id", "condition_id"}, "run")


def test_require_fields_passes_when_all_present():
    """No error when every required field exists."""
    require_fields({"task_id": "t01", "condition_id": "1"}, {"task_id", "condition_id"}, "run")


def test_require_fields_detects_subset_missing():
    """Only the actually-missing fields appear in the message."""
    with pytest.raises(ContractError, match="schedule: missing fields: variant_id"):
        require_fields({"task_id": "t01"}, {"task_id", "variant_id"}, "schedule")


# --- validate_identifier ---


def test_identifier_rejects_path_escape():
    """Path traversal in identifiers is a contract violation."""
    with pytest.raises(ContractError, match="condition_id"):
        validate_identifier("../6a", "condition_id")


def test_identifier_rejects_slash():
    """Forward slashes escape the expected flat namespace."""
    with pytest.raises(ContractError, match="task_id"):
        validate_identifier("tasks/01", "task_id")


def test_identifier_rejects_empty():
    """Empty string is not a valid identifier."""
    with pytest.raises(ContractError, match="run_id"):
        validate_identifier("", "run_id")


def test_identifier_accepts_valid_values():
    """Alphanumeric with hyphens and underscores passes."""
    assert validate_identifier("task-01", "task_id") == "task-01"
    assert validate_identifier("6a", "condition_id") == "6a"
    assert validate_identifier("v1", "variant_id") == "v1"


# --- load_json ---


def test_load_json_reads_valid_file(tmp_path: Path):
    """Round-trip through a temp file."""
    target = tmp_path / "test.json"
    target.write_text(json.dumps({"key": "value"}))
    data = load_json(target)
    assert data == {"key": "value"}


def test_load_json_rejects_missing_file(tmp_path: Path):
    """Non-existent path raises ContractError, not FileNotFoundError."""
    with pytest.raises(ContractError, match="not found"):
        load_json(tmp_path / "nope.json")


def test_load_json_rejects_malformed_json(tmp_path: Path):
    """Broken JSON raises ContractError, not json.JSONDecodeError."""
    target = tmp_path / "bad.json"
    target.write_text("{not valid json")
    with pytest.raises(ContractError, match="invalid JSON"):
        load_json(target)
