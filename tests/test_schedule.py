"""Randomized schedule generation tests (RED phase)."""

from collections import Counter
from pathlib import Path

import pytest

from tdd_ablation.contracts import ContractError
from tdd_ablation.schedule import (
    ScheduleRow,
    build_confirmation_schedule,
    build_screening_schedule,
    write_schedule,
)

TASKS = [f"task-{i:02d}" for i in range(1, 13)]


def test_screening_schedule_default_repetitions_yield_576_balanced_rows():
    """12 tasks x 8 conditions x 6 repetitions = 576 balanced rows."""
    rows = build_screening_schedule(TASKS, seed=17)
    assert len(rows) == 576
    # Each (task_id, condition_id, variant_id) combination should appear exactly 2 times (6 repetitions / 3 variants)
    counts = Counter((r.task_id, r.condition_id, r.variant_id) for r in rows)
    assert set(counts.values()) == {2}


def test_repetitions_scale_row_count_and_stay_balanced():
    """9 repetitions yield 864 rows, 3 per variant."""
    rows = build_screening_schedule(TASKS, seed=17, repetitions=9)
    assert len(rows) == 864
    counts = Counter((r.task_id, r.condition_id, r.variant_id) for r in rows)
    assert set(counts.values()) == {3}


def test_repetitions_not_divisible_by_variants_are_rejected():
    """Repetitions not divisible by 3 (number of variants) are rejected."""
    with pytest.raises(ContractError, match="repetitions"):
        build_screening_schedule(TASKS, seed=17, repetitions=7)


def test_same_seed_produces_same_order():
    """Deterministic order for same seed."""
    s1 = build_screening_schedule(TASKS, seed=17)
    s2 = build_screening_schedule(TASKS, seed=17)
    assert s1 == s2


def test_confirmation_schedule_generation():
    """Confirmation schedule generates paired comparisons across conditions."""
    pairs = [("1", "2"), ("5", "6c")]
    rows = build_confirmation_schedule(TASKS, condition_pairs=pairs, seed=42, repetitions=12)
    # 12 tasks x 2 pairs x 2 conditions per pair x 12 reps = 576 rows
    assert len(rows) == 12 * 2 * 2 * 12
    assert all(r.phase == "confirmation" for r in rows)


def test_write_schedule_csv(tmp_path: Path):
    """write_schedule writes valid CSV file."""
    rows = build_screening_schedule(TASKS[:2], seed=1, repetitions=3)
    target = tmp_path / "schedule.csv"
    write_schedule(rows, target)
    assert target.exists()
    lines = target.read_text().splitlines()
    assert lines[0].startswith("run_id,phase,order,task_id,condition_id")
    assert len(lines) == len(rows) + 1
