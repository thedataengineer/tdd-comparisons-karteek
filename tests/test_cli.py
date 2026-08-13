"""CLI and end-to-end integration tests."""

import json
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


def test_cli_validate_rejects_missing_study(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    missing = tmp_path / "missing-study"

    res = run_cli(["validate", "--study", str(missing)])

    assert res == 1
    assert "study directory not found" in capsys.readouterr().err


def test_cli_validate_requires_prompt_registry(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    study_dir = tmp_path / "study"
    study_dir.mkdir()
    (study_dir / "preregistration.json").write_text(
        Path("study/preregistration.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    res = run_cli(["validate", "--study", str(study_dir)])

    assert res == 1
    assert "prompts/conditions.json" in capsys.readouterr().err


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


def test_cli_report_rejects_missing_results(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    study_dir = tmp_path / "study"
    study_dir.mkdir()

    res = run_cli(["report", "--study", str(study_dir), "--output", str(tmp_path / "out")])

    assert res == 1
    assert "results.json" in capsys.readouterr().err


def test_cli_report_renders_study_results(tmp_path: Path):
    study_dir = tmp_path / "study"
    study_dir.mkdir()
    (study_dir / "results.json").write_text(
        json.dumps(
            {
                "study_name": "Controlled Trial",
                "total_runs": 24,
                "adoption_decision": {"adopt": False, "reasons": ["quality threshold missed"]},
            }
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "reports"

    res = run_cli(["report", "--study", str(study_dir), "--output", str(out_dir)])

    report = (out_dir / "executive-report.md").read_text(encoding="utf-8")
    assert res == 0
    assert "# Controlled Trial" in report
    assert "Total Analyzed Runs:** 24" in report
    assert "Decision:** REJECT" in report


@pytest.mark.parametrize(
    "results",
    [
        {"study_name": 123, "total_runs": 24, "adoption_decision": {"adopt": False, "reasons": []}},
        {"study_name": "Trial", "total_runs": "24", "adoption_decision": {"adopt": False, "reasons": []}},
        {"study_name": "Trial", "total_runs": True, "adoption_decision": {"adopt": False, "reasons": []}},
        {
            "study_name": "Trial",
            "total_runs": 24,
            "adoption_decision": {"adopt": False, "reasons": [{"bad": "shape"}]},
        },
    ],
)
def test_cli_report_rejects_malformed_result_types(
    tmp_path: Path,
    results: dict[str, object],
    capsys: pytest.CaptureFixture[str],
):
    study_dir = tmp_path / "study"
    study_dir.mkdir()
    (study_dir / "results.json").write_text(json.dumps(results), encoding="utf-8")

    res = run_cli(["report", "--study", str(study_dir), "--output", str(tmp_path / "out")])

    assert res == 1
    assert "Contract error:" in capsys.readouterr().err
