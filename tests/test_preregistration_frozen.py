"""Frozen preregistration, prompts, and power analysis test (RED phase)."""

from pathlib import Path

from tdd_ablation.contracts import load_json
from tdd_ablation.preregistration import validate_preregistration
from tdd_ablation.prompts import validate_prompt_registry


def test_frozen_preregistration_validates():
    prereg_path = Path("study/preregistration.json")
    assert prereg_path.exists()
    data = load_json(prereg_path)
    validate_preregistration(data)
    assert len(data["hypotheses"]) == 8


def test_frozen_power_analysis_exists():
    power_path = Path("study/power-analysis.json")
    assert power_path.exists()
    data = load_json(power_path)
    assert data["task_count"] == 12
    assert data["allocated_per_cell"] >= 6


def test_prompt_equivalence_review_exists():
    review_path = Path("study/prompt-equivalence-review.csv")
    assert review_path.exists()
    lines = review_path.read_text().splitlines()
    assert len(lines) >= 25  # Header + 24 prompt variants
