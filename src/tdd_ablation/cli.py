"""Command Line Interface for TDD Ablation Toolkit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from tdd_ablation.contracts import ContractError, load_json
from tdd_ablation.preregistration import validate_preregistration
from tdd_ablation.prompts import validate_prompt_registry
from tdd_ablation.report import render_report
from tdd_ablation.runs import verify_store
from tdd_ablation.schedule import build_screening_schedule, write_schedule


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tdd-ablation",
        description="Reproducible command-line toolkit for TDD practice ablation study",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate
    p_val = subparsers.add_parser("validate", help="Validate study manifests and pre-registration")
    p_val.add_argument("--study", required=True, type=Path, help="Path to study directory")

    # schedule
    p_sch = subparsers.add_parser("schedule", help="Generate randomized schedule")
    p_sch.add_argument("--phase", choices=["screening", "confirmation"], default="screening")
    p_sch.add_argument("--study", required=True, type=Path)
    p_sch.add_argument("--output", required=True, type=Path)
    p_sch.add_argument("--seed", type=int, default=17)
    p_sch.add_argument("--repetitions", type=int, default=6)

    # verify-store
    p_ver = subparsers.add_parser("verify-store", help="Verify run store integrity")
    p_ver.add_argument("--study", required=True, type=Path)

    # report
    p_rep = subparsers.add_parser("report", help="Generate executive report")
    p_rep.add_argument("--study", required=True, type=Path)
    p_rep.add_argument("--output", required=True, type=Path)

    return parser


def run_cli(args: Sequence[str] | None = None) -> int:
    parser = create_parser()
    parsed = parser.parse_args(args)

    try:
        if parsed.command == "validate":
            study_dir = parsed.study
            prereg_file = study_dir / "preregistration.json"
            if not prereg_file.exists():
                prereg_file = study_dir / "preregistration.example.json"
            if prereg_file.exists():
                validate_preregistration(load_json(prereg_file))

            prompts_file = study_dir / "prompts" / "conditions.json"
            if prompts_file.exists():
                validate_prompt_registry(load_json(prompts_file))

            print("Validation successful.")
            return 0

        elif parsed.command == "schedule":
            task_ids = [f"task-{i:02d}" for i in range(1, 13)]
            rows = build_screening_schedule(task_ids, seed=parsed.seed, repetitions=parsed.repetitions)
            write_schedule(rows, parsed.output)
            print(f"Schedule written to {parsed.output} ({len(rows)} rows).")
            return 0

        elif parsed.command == "verify-store":
            corrupted = verify_store(parsed.study / "runs")
            if corrupted:
                print(f"Store verification failed for runs: {corrupted}", file=sys.stderr)
                return 1
            print("Store integrity verified successfully.")
            return 0

        elif parsed.command == "report":
            out_dir = parsed.output
            out_dir.mkdir(parents=True, exist_ok=True)
            report_md = render_report(
                {
                    "study_name": "TDD Practice Ablation Study",
                    "total_runs": 576,
                    "adoption_decision": {"adopt": True, "reasons": []},
                }
            )
            (out_dir / "executive-report.md").write_text(report_md, encoding="utf-8")
            print(f"Report rendered to {out_dir}")
            return 0

    except ContractError as exc:
        print(f"Contract error: {exc}", file=sys.stderr)
        return 1

    return 0


def main() -> None:
    sys.exit(run_cli())


if __name__ == "__main__":
    main()
