"""Condition prompts registration, prompt hashing, and prompt resolution."""

from __future__ import annotations

import hashlib
from typing import Any

from tdd_ablation.contracts import ContractError, require_fields, validate_identifier

EXPECTED_CONDITIONS = {"1", "2", "3", "4", "5", "6a", "6b", "6c"}
EXPECTED_VARIANTS = {"v1", "v2", "v3"}


def prompt_hash(text: str) -> str:
    """Compute SHA-256 hex digest for prompt text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_prompt_registry(data: dict[str, Any]) -> None:
    """Validate condition prompt registry structure and hash uniqueness."""
    require_fields(data, {"conditions"}, "prompt_registry")
    conditions = data.get("conditions")
    if not isinstance(conditions, list):
        raise ContractError("prompt_registry: conditions must be a list")

    seen_conditions: set[str] = set()
    seen_hashes: set[str] = set()

    for idx, cond in enumerate(conditions):
        if not isinstance(cond, dict):
            raise ContractError(f"prompt_registry: condition[{idx}] must be a dict")
        require_fields(cond, {"id", "name", "variants"}, f"prompt_registry: condition[{idx}]")

        cond_id = validate_identifier(str(cond["id"]), f"condition[{idx}].id")
        if cond_id not in EXPECTED_CONDITIONS:
            raise ContractError(f"prompt_registry: unexpected condition_id: {cond_id!r}")
        if cond_id in seen_conditions:
            raise ContractError(f"prompt_registry: duplicate condition_id: {cond_id!r}")
        seen_conditions.add(cond_id)

        variants = cond.get("variants")
        if not isinstance(variants, list) or len(variants) != 3:
            raise ContractError(
                f"prompt_registry: condition {cond_id} must have exactly 3 variants"
            )

        seen_variants: set[str] = set()
        for v_idx, var in enumerate(variants):
            if not isinstance(var, dict):
                raise ContractError(
                    f"prompt_registry: condition {cond_id}.variant[{v_idx}] must be a dict"
                )
            require_fields(
                var,
                {
                    "id",
                    "text",
                    "hash",
                    "obligations",
                    "prohibitions",
                    "completion_criteria",
                },
                f"prompt_registry: condition {cond_id}.variant[{v_idx}]",
            )

            var_id = validate_identifier(str(var["id"]), f"variant[{v_idx}].id")
            if var_id not in EXPECTED_VARIANTS:
                raise ContractError(f"prompt_registry: unexpected variant_id: {var_id!r}")
            if var_id in seen_variants:
                raise ContractError(
                    f"prompt_registry: duplicate variant_id {var_id!r} in condition {cond_id}"
                )
            seen_variants.add(var_id)

            text = var.get("text", "")
            expected_h = prompt_hash(text)
            declared_h = var.get("hash")
            if declared_h != expected_h:
                raise ContractError(
                    f"prompt_registry: hash mismatch for {cond_id}/{var_id}: "
                    f"declared {declared_h!r}, calculated {expected_h!r}"
                )

            if declared_h in seen_hashes:
                raise ContractError(
                    f"prompt_registry: duplicate prompt hash across variants: {declared_h!r}"
                )
            seen_hashes.add(declared_h)

    if seen_conditions != EXPECTED_CONDITIONS:
        missing = sorted(EXPECTED_CONDITIONS - seen_conditions)
        raise ContractError(f"prompt_registry: missing conditions: {missing}")


def resolve_prompt(
    condition_id: str,
    variant_id: str,
    registry_data: dict[str, Any] | None = None,
) -> str:
    """Resolve prompt text for condition_id and variant_id."""
    if registry_data is None:
        raise ContractError("registry_data must be provided")

    validate_prompt_registry(registry_data)

    for cond in registry_data["conditions"]:
        if cond["id"] == condition_id:
            for var in cond["variants"]:
                if var["id"] == variant_id:
                    return str(var["text"])
            raise ContractError(f"unknown variant_id: {variant_id!r}")

    raise ContractError(f"unknown condition_id: {condition_id!r}")
