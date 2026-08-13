"""Hidden evaluator catalog test (RED phase)."""

from pathlib import Path

import pytest

from tdd_ablation.contracts import load_json
from tdd_ablation.tasks import validate_task_manifest


def test_every_hidden_test_has_business_behavior_and_severity():
    tasks_dir = Path("study/tasks")
    task_files = sorted(list(tasks_dir.glob("task-*.json")))
    assert len(task_files) == 12

    for tf in task_files:
        data = load_json(tf)
        validate_task_manifest(data, draft=False)
        hidden = data["hidden_tests"]
        assert len(hidden) >= 2
        for node_id, info in hidden.items():
            assert "business_behavior" in info
            assert info["severity"] in ("low", "medium", "high", "critical")


def test_hidden_evaluator_directories_exist():
    for i in range(1, 13):
        hidden_dir = Path(f"study/hidden/task-{i:02d}")
        assert hidden_dir.exists()
        assert (hidden_dir / "test_evaluator.py").exists()
