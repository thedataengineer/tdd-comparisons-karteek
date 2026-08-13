"""Condition prompts and prompt sensitivity tests (RED phase)."""

from pathlib import Path

import pytest

from tdd_ablation.contracts import ContractError, load_json
from tdd_ablation.prompts import (
    prompt_hash,
    resolve_prompt,
    validate_prompt_registry,
)


@pytest.fixture
def prompt_registry_path() -> Path:
    return Path("study/prompts/conditions.json")


def test_prompt_hash_is_deterministic_sha256():
    """Prompt hash produces SHA-256 hex string."""
    h1 = prompt_hash("Hello world")
    h2 = prompt_hash("Hello world")
    assert h1 == h2
    assert len(h1) == 64
    assert prompt_hash("Hello world ") != h1


def test_every_condition_has_three_distinct_variants():
    """Registry validates 8 conditions x 3 distinct prompt variants."""
    data = load_json(Path("study/prompts/conditions.json"))
    validate_prompt_registry(data)
    conditions = data["conditions"]
    assert len(conditions) == 8
    expected_ids = {"1", "2", "3", "4", "5", "6a", "6b", "6c"}
    assert {c["id"] for c in conditions} == expected_ids

    for c in conditions:
        variants = c["variants"]
        assert len(variants) == 3
        hashes = {v["hash"] for v in variants}
        assert len(hashes) == 3  # All distinct


def test_duplicate_prompt_text_is_rejected():
    """Duplicate prompt hash within or across variants raises ContractError."""
    data = load_json(Path("study/prompts/conditions.json"))
    # Duplicate first variant text to second
    data["conditions"][0]["variants"][1]["text"] = data["conditions"][0]["variants"][0]["text"]
    data["conditions"][0]["variants"][1]["hash"] = data["conditions"][0]["variants"][0]["hash"]
    with pytest.raises(ContractError, match="duplicate prompt hash"):
        validate_prompt_registry(data)


def test_resolve_prompt_returns_variant_text():
    """resolve_prompt returns exact text for condition and variant ID."""
    data = load_json(Path("study/prompts/conditions.json"))
    text = resolve_prompt("1", "v1", registry_data=data)
    assert isinstance(text, str)
    assert len(text) > 0


def test_resolve_prompt_rejects_unknown_condition_or_variant():
    """Invalid condition or variant ID raises ContractError."""
    data = load_json(Path("study/prompts/conditions.json"))
    with pytest.raises(ContractError, match="unknown condition_id"):
        resolve_prompt("99", "v1", registry_data=data)

    with pytest.raises(ContractError, match="unknown variant_id"):
        resolve_prompt("1", "v99", registry_data=data)
