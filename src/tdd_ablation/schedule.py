"""Randomized screening and confirmation schedule generation."""

from __future__ import annotations

import csv
import random
from dataclasses import asdict, dataclass
from pathlib import Path

from tdd_ablation.contracts import ContractError, validate_identifier

SCREENING_CONDITIONS = ["1", "2", "3", "4", "5", "6a", "6b", "6c"]
PROMPT_VARIANTS = ["v1", "v2", "v3"]


@dataclass(frozen=True)
class ScheduleRow:
    run_id: str
    phase: str
    order: int
    task_id: str
    condition_id: str
    baseline_condition_id: str | None
    variant_id: str
    repetition: int
    seed: int


def build_screening_schedule(
    task_ids: list[str],
    seed: int,
    repetitions: int = 6,
) -> list[ScheduleRow]:
    """Build balanced randomized screening schedule."""
    if repetitions % len(PROMPT_VARIANTS) != 0 or repetitions <= 0:
        raise ContractError(
            f"repetitions ({repetitions}) must be a positive multiple of variant count ({len(PROMPT_VARIANTS)})"
        )
    if not task_ids:
        raise ContractError("task_ids list cannot be empty")

    for tid in task_ids:
        validate_identifier(tid, "task_id")

    reps_per_variant = repetitions // len(PROMPT_VARIANTS)
    rows_unshuffled: list[tuple[str, str, str, int]] = []

    for tid in task_ids:
        for cid in SCREENING_CONDITIONS:
            rep_count = 0
            for var_id in PROMPT_VARIANTS:
                for _ in range(reps_per_variant):
                    rep_count += 1
                    rows_unshuffled.append((tid, cid, var_id, rep_count))

    rng = random.Random(seed)
    shuffled = list(rows_unshuffled)
    rng.shuffle(shuffled)

    schedule: list[ScheduleRow] = []
    for idx, (tid, cid, var_id, rep) in enumerate(shuffled, start=1):
        run_id = f"scr-{seed}-{idx:04d}"
        schedule.append(
            ScheduleRow(
                run_id=run_id,
                phase="screening",
                order=idx,
                task_id=tid,
                condition_id=cid,
                baseline_condition_id=None,
                variant_id=var_id,
                repetition=rep,
                seed=seed,
            )
        )

    return schedule


def build_confirmation_schedule(
    task_ids: list[str],
    condition_pairs: list[tuple[str, str]],
    seed: int,
    repetitions: int = 12,
) -> list[ScheduleRow]:
    """Build paired randomized confirmation schedule."""
    if repetitions % len(PROMPT_VARIANTS) != 0 or repetitions <= 0:
        raise ContractError(
            f"repetitions ({repetitions}) must be a positive multiple of variant count ({len(PROMPT_VARIANTS)})"
        )
    if not task_ids:
        raise ContractError("task_ids list cannot be empty")
    if not condition_pairs:
        raise ContractError("condition_pairs list cannot be empty")

    reps_per_variant = repetitions // len(PROMPT_VARIANTS)
    rows_unshuffled: list[tuple[str, str, str | None, str, int]] = []

    for tid in task_ids:
        for baseline, treatment in condition_pairs:
            for cid, base_id in [(baseline, None), (treatment, baseline)]:
                rep_count = 0
                for var_id in PROMPT_VARIANTS:
                    for _ in range(reps_per_variant):
                        rep_count += 1
                        rows_unshuffled.append((tid, cid, base_id, var_id, rep_count))

    rng = random.Random(seed)
    shuffled = list(rows_unshuffled)
    rng.shuffle(shuffled)

    schedule: list[ScheduleRow] = []
    for idx, (tid, cid, base_id, var_id, rep) in enumerate(shuffled, start=1):
        run_id = f"cnf-{seed}-{idx:04d}"
        schedule.append(
            ScheduleRow(
                run_id=run_id,
                phase="confirmation",
                order=idx,
                task_id=tid,
                condition_id=cid,
                baseline_condition_id=base_id,
                variant_id=var_id,
                repetition=rep,
                seed=seed,
            )
        )

    return schedule


def write_schedule(rows: list[ScheduleRow], path: Path) -> None:
    """Write schedule rows to CSV file."""
    if not rows:
        raise ContractError("rows list cannot be empty")

    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(asdict(rows[0]).keys())

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
