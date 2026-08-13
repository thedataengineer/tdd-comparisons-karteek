"""Study portfolio validation test (RED phase)."""

from collections import Counter
from pathlib import Path

from tdd_ablation.contracts import load_json
from tdd_ablation.tasks import validate_task_manifest


def test_screening_portfolio_has_two_tasks_per_family():
    tasks_dir = Path("study/tasks")
    task_files = sorted(list(tasks_dir.glob("task-*.json")))
    assert len(task_files) == 12

    families = []
    for tf in task_files:
        data = load_json(tf)
        validate_task_manifest(data, draft=True)
        families.append(data["family"])

    assert Counter(families) == {
        "parsing": 2,
        "state": 2,
        "concurrency": 2,
        "api": 2,
        "transformation": 2,
        "defect_repair": 2,
    }


def test_public_specs_exist_for_all_12_tasks():
    public_dir = Path("study/public")
    spec_files = sorted(list(public_dir.glob("task-*.md")))
    assert len(spec_files) == 12
