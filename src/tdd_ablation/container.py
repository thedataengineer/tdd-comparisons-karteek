"""Container runner command builder for locked execution isolation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tdd_ablation.contracts import ContractError

ALLOWED_RUNNERS = {"docker", "podman"}


def build_container_command(
    task_manifest: dict[str, Any],
    run_dir: Path,
    output_dir: Path,
    runner_binary: str = "docker",
) -> list[str]:
    """Build isolated container run CLI command with strict security flags."""
    if runner_binary not in ALLOWED_RUNNERS:
        raise ContractError(
            f"unsupported container runner {runner_binary!r}, expected one of {sorted(ALLOWED_RUNNERS)}"
        )

    limits = task_manifest.get("resource_limits", {})
    image = task_manifest.get("container_image_digest", "python:3.12.5-slim")

    cmd = [
        runner_binary,
        "run",
        "--rm",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
    ]

    if not limits.get("network_enabled", False):
        cmd.extend(["--network", "none"])

    if "cpu_cores" in limits:
        cmd.extend(["--cpus", str(limits["cpu_cores"])])

    if "memory_mb" in limits:
        cmd.extend(["--memory", f"{limits['memory_mb']}m"])

    if "max_pids" in limits:
        cmd.extend(["--pids-limit", str(limits["max_pids"])])

    cmd.extend(
        [
            "-v",
            f"{run_dir.resolve()}:/submission:ro",
            "-v",
            f"{output_dir.resolve()}:/output:rw",
            image,
        ]
    )

    return cmd
