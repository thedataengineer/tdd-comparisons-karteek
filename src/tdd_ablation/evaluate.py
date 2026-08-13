"""JUnit XML evaluation parser and severity-weighted scoring."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tdd_ablation.contracts import ContractError

SEVERITY_WEIGHTS = {
    "low": 1,
    "medium": 2,
    "high": 4,
    "critical": 8,
}


@dataclass(frozen=True)
class EvaluationRecord:
    passed_count: int
    failed_count: int
    skipped_count: int
    total_count: int
    passed_weight: int
    failed_weight: int
    total_weight: int
    score: float
    high_severity_defects: int


def parse_junit(path: Path, severity_map: dict[str, str]) -> EvaluationRecord:
    """Parse JUnit XML file and calculate severity-weighted scores."""
    if not path.exists():
        raise ContractError(f"JUnit XML file not found: {path}")

    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except Exception as exc:
        raise ContractError(f"failed to parse JUnit XML {path}: {exc}") from exc

    passed_count = 0
    failed_count = 0
    skipped_count = 0
    passed_weight = 0
    failed_weight = 0
    high_severity_defects = 0

    testcases = root.findall(".//testcase")
    if not testcases:
        testcases = root.findall("testcase")

    for tc in testcases:
        name = tc.get("name", "")
        classname = tc.get("classname", "")
        key = f"{classname}::{name}" if classname else name

        severity = severity_map.get(key, severity_map.get(name, "low"))
        weight = SEVERITY_WEIGHTS.get(severity, 1)

        if tc.find("skipped") is not None:
            skipped_count += 1
            continue

        is_failure = tc.find("failure") is not None or tc.find("error") is not None

        if is_failure:
            failed_count += 1
            failed_weight += weight
            if severity in ("high", "critical"):
                high_severity_defects += 1
        else:
            passed_count += 1
            passed_weight += weight

    total_count = passed_count + failed_count
    total_weight = passed_weight + failed_weight
    score = (passed_weight / total_weight) if total_weight > 0 else 0.0

    return EvaluationRecord(
        passed_count=passed_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        total_count=total_count,
        passed_weight=passed_weight,
        failed_weight=failed_weight,
        total_weight=total_weight,
        score=score,
        high_severity_defects=high_severity_defects,
    )
