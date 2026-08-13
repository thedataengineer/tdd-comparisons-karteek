"""CLI and end-to-end integration tests."""

from pathlib import Path

import pytest

from tdd_ablation.cli import main, run_cli
from tdd_ablation.report import render_report


def test_cli_help_exits_cleanly():
    with pytest.raises(SystemExit) as exc:
        run_cli(["--help"])
    assert exc.value.code == 0


def test_render_report_produces_markdown():
    data = {
        "study_name": "TDD Practice Ablation Study",
        "total_runs": 576,
        "adoption_decision": {"adopt": True, "reasons": []},
    }
    report_md = render_report(data)
    assert "# TDD Practice Ablation Study" in report_md
    assert "- **Decision:** ADOPT" in report_md


def test_render_report_produces_rejection_reasons():
    data = {
        "study_name": "TDD Practice Ablation Study",
        "total_runs": 576,
        "adoption_decision": {"adopt": False, "reasons": ["underpowered sample"]},
    }
    report_md = render_report(data)
    assert "- **Decision:** REJECT" in report_md
    assert "underpowered sample" in report_md


def test_cli_validate_command():
    res = run_cli(["validate", "--study", "study"])
    assert res == 0


def test_cli_schedule_command(tmp_path: Path):
    target = tmp_path / "schedule.csv"
    res = run_cli(["schedule", "--study", "study", "--output", str(target), "--seed", "42", "--repetitions", "6"])
    assert res == 0
    assert target.exists()


def test_cli_verify_store_command(tmp_path: Path):
    res = run_cli(["verify-store", "--study", "study"])
    assert res == 0


def test_cli_report_command(tmp_path: Path):
    out_dir = tmp_path / "reports"
    res = run_cli(["report", "--study", "study", "--output", str(out_dir)])
    assert res == 0
    assert (out_dir / "executive-report.md").exists()
