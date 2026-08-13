"""End-to-end reproduction and workflow integration tests."""

from pathlib import Path

from tdd_ablation.cli import run_cli
from tdd_ablation.hashing import hash_tree


def test_reference_study_replays_identically(tmp_path: Path):
    out_one = tmp_path / "run-one"
    out_two = tmp_path / "run-two"

    res1 = run_cli(["report", "--study", "study", "--output", str(out_one)])
    res2 = run_cli(["report", "--study", "study", "--output", str(out_two)])

    assert res1 == 0
    assert res2 == 0
    assert hash_tree(out_one) == hash_tree(out_two)


def test_cli_validate_study_directory():
    res = run_cli(["validate", "--study", "study"])
    assert res == 0
