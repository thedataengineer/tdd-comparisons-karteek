"""Task manifests loading and validation."""

from __future__ import annotations

from typing import Any

from tdd_ablation.contracts import ContractError, require_fields, validate_identifier
from tdd_ablation.reliability import SEVERITY_LEVELS

TASK_FAMILIES = {
    "parsing",
    "state",
    "concurrency",
    "api",
    "transformation",
    "defect_repair",
}


def validate_task_manifest(data: dict[str, Any], draft: bool = False) -> None:
    """Validate task manifest fields, family, and hidden test mapping."""
    base_required = {
        "id",
        "family",
        "public_spec_path",
        "hidden_evaluator_path",
        "severity_rubric_version",
        "dependency_lock_hash",
        "python_version",
        "container_image_digest",
        "resource_limits",
    }
    if not draft:
        base_required.add("hidden_tests")

    require_fields(data, base_required, "task_manifest")

    task_id = validate_identifier(str(data["id"]), "task_manifest.id")
    family = str(data["family"])
    if family not in TASK_FAMILIES:
        raise ContractError(
            f"task_manifest {task_id}: invalid family {family!r}, expected one of {sorted(TASK_FAMILIES)}"
        )

    limits = data.get("resource_limits")
    if not isinstance(limits, dict):
        raise ContractError(f"task_manifest {task_id}: resource_limits must be a dict")
    require_fields(
        limits,
        {"cpu_cores", "memory_mb", "max_pids", "timeout_seconds", "network_enabled"},
        f"task_manifest {task_id}.resource_limits",
    )

    if not draft:
        hidden = data.get("hidden_tests")
        if not isinstance(hidden, dict):
            raise ContractError(f"task_manifest {task_id}: hidden_tests must be a dict")
        if not hidden:
            raise ContractError(f"task_manifest {task_id}: hidden_tests mapping cannot be empty")

        for node_id, test_info in hidden.items():
            if not isinstance(test_info, dict):
                raise ContractError(
                    f"task_manifest {task_id}: hidden_tests[{node_id!r}] must be a dict"
                )
            require_fields(
                test_info,
                {"business_behavior", "severity"},
                f"task_manifest {task_id}.hidden_tests[{node_id!r}]",
            )
            severity = str(test_info["severity"])
            if severity not in SEVERITY_LEVELS:
                raise ContractError(
                    f"task_manifest {task_id}: hidden_tests[{node_id!r}] invalid severity {severity!r}"
                )
