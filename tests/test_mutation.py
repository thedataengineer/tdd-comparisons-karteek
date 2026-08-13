"""Mutation protocol and scoring tests (RED phase)."""

import json
from pathlib import Path

import pytest

from tdd_ablation.contracts import ContractError
from tdd_ablation.mutation import (
    MutationResult,
    mutation_score,
    parse_mutation_results,
    validate_mutation_protocol,
)


def test_primary_denominator_keeps_timeouts_suspicious_and_equivalents():
    result = MutationResult(
        killed=8,
        survived=1,
        suspicious=1,
        timed_out=1,
        equivalent=1,
    )
    # Total generated mutants = 8 + 1 + 1 + 1 + 1 = 12
    # Score = killed / total = 8 / 12 = 0.6667
    assert mutation_score(result, exclude_equivalent=False) == pytest.approx(8 / 12)
    # Sensitivity score excluding adjudicated equivalents = 8 / (12 - 1) = 8 / 11
    assert mutation_score(result, exclude_equivalent=True) == pytest.approx(8 / 11)


def test_parse_mutmut_meta_results(tmp_path: Path):
    meta_json = {
        "exit_code_by_key": {
            "calc.x_add__mutmut_1": 1,  # killed
            "calc.x_add__mutmut_2": 0,  # survived
            "calc.x_add__mutmut_3": 2,  # timed_out
        },
        "type_check_error_by_key": {},
        "durations_by_key": {
            "calc.x_add__mutmut_1": 0.01,
            "calc.x_add__mutmut_2": 0.02,
            "calc.x_add__mutmut_3": 1.00,
        },
        "estimated_durations_by_key": {},
    }
    meta_file = tmp_path / "calc.py.meta"
    meta_file.write_text(json.dumps(meta_json), encoding="utf-8")

    res = parse_mutation_results(meta_file)
    assert res.killed == 1
    assert res.survived == 1
    assert res.timed_out == 1
    assert res.total == 3


def test_validate_mutation_protocol():
    proto_data = {
        "python_version": "3.12.5",
        "mutmut_version": "3.6.0",
        "operator_set": "full_unfiltered",
        "timeout_multiplier": 2.0,
        "extraction_method": "mutants_meta_json",
    }
    validate_mutation_protocol(proto_data)
