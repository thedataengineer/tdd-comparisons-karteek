"""Mutation protocol definition, mutmut 3.6.0 result ingestion, and scoring."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tdd_ablation.contracts import ContractError, load_json, require_fields


@dataclass(frozen=True)
class MutationResult:
    killed: int = 0
    survived: int = 0
    suspicious: int = 0
    timed_out: int = 0
    equivalent: int = 0

    @property
    def total(self) -> int:
        return self.killed + self.survived + self.suspicious + self.timed_out + self.equivalent


def validate_mutation_protocol(data: dict[str, Any]) -> None:
    """Validate mutation protocol settings dict."""
    require_fields(
        data,
        {
            "python_version",
            "mutmut_version",
            "operator_set",
            "timeout_multiplier",
            "extraction_method",
        },
        "mutation_protocol",
    )
    if data.get("mutmut_version") != "3.6.0":
        raise ContractError(f"unsupported mutmut version: {data.get('mutmut_version')!r}")


def parse_mutation_results(meta_path: Path) -> MutationResult:
    """Parse mutmut 3.6.0 JSON meta file (mutants/*.meta)."""
    data = load_json(meta_path)

    exit_codes = data.get("exit_code_by_key")
    if not isinstance(exit_codes, dict):
        raise ContractError(f"invalid mutmut meta file {meta_path}: missing exit_code_by_key")

    killed = 0
    survived = 0
    timed_out = 0
    suspicious = 0

    for code in exit_codes.values():
        if code == 1:
            killed += 1
        elif code == 0:
            survived += 1
        elif code in (2, 124, 137):  # timeout exit codes
            timed_out += 1
        else:
            suspicious += 1

    return MutationResult(
        killed=killed,
        survived=survived,
        suspicious=suspicious,
        timed_out=timed_out,
        equivalent=0,
    )


def mutation_score(result: MutationResult, exclude_equivalent: bool = False) -> float:
    """Compute mutation score (killed / denominator)."""
    denom = result.total - (result.equivalent if exclude_equivalent else 0)
    if denom <= 0:
        return 0.0
    return result.killed / denom
