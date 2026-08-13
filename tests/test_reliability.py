"""Reliability module tests."""

import pytest

from tdd_ablation.contracts import ContractError
from tdd_ablation.reliability import (
    validate_severity_calibration,
    weighted_kappa,
)


def test_kappa_length_mismatch_raises_error():
    with pytest.raises(ContractError, match="length mismatch"):
        weighted_kappa([0, 1], [0, 1, 2])


def test_severity_calibration_requires_two_reviewers():
    with pytest.raises(ContractError, match="must contain exactly two reviewers"):
        validate_severity_calibration({"r1": [0, 1]})
