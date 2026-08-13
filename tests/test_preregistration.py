"""Pre-registration and power analysis tests (RED phase)."""

import pytest

from tdd_ablation.contracts import ContractError
from tdd_ablation.preregistration import (
    required_runs,
    validate_preregistration,
)


def test_power_calculation_inflates_for_clustering_and_attrition():
    """Design effect and attrition inflate required run count."""
    baseline = required_runs(
        effect=0.05,
        standard_deviation=0.10,
        alpha=0.05,
        power=0.80,
        design_effect=1.0,
        attrition=0.0,
    )
    adjusted = required_runs(
        effect=0.05,
        standard_deviation=0.10,
        alpha=0.05,
        power=0.80,
        design_effect=1.5,
        attrition=0.10,
    )
    assert adjusted > baseline


def test_power_calculation_rejects_invalid_inputs():
    """Invalid parameter bounds trigger ContractError."""
    with pytest.raises(ContractError, match="effect must be positive"):
        required_runs(0.0, 0.10, 0.05, 0.80, 1.0, 0.0)

    with pytest.raises(ContractError, match="attrition must be in"):
        required_runs(0.05, 0.10, 0.05, 0.80, 1.0, 1.0)


def test_preregistration_requires_confirmatory_success_rule():
    """Preregistration dict missing confirmation_success fails validation."""
    with pytest.raises(ContractError, match="missing fields: confirmation_success"):
        validate_preregistration({"hypotheses": []})


def test_example_file_validates():
    """study/preregistration.example.json is valid according to validate_preregistration."""
    from pathlib import Path

    from tdd_ablation.contracts import load_json

    data = load_json(Path("study/preregistration.example.json"))
    validate_preregistration(data)

