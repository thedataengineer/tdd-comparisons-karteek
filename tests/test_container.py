"""Container command building and evaluator tests (RED phase)."""

from pathlib import Path

import pytest

from tdd_ablation.container import build_container_command
from tdd_ablation.contracts import ContractError
from tdd_ablation.evaluate import parse_junit


def test_container_command_applies_security_limits():
    task_manifest = {
        "id": "task-01",
        "container_image_digest": "sha256:abcd1234efgh5678",
        "resource_limits": {
            "cpu_cores": 1.5,
            "memory_mb": 512,
            "max_pids": 32,
            "timeout_seconds": 30,
            "network_enabled": False,
        },
    }
    cmd = build_container_command(task_manifest, Path("/run_dir"), Path("/out_dir"))
    joined = " ".join(cmd)

    assert "docker run --rm" in joined
    assert "--network none" in joined
    assert "--read-only" in joined
    assert "--cap-drop ALL" in joined
    assert "--pids-limit 32" in joined
    assert "--memory 512m" in joined
    assert "--cpus 1.5" in joined
    assert "no-new-privileges" in joined


def test_container_command_rejects_invalid_runner():
    task_manifest = {
        "id": "task-01",
        "container_image_digest": "sha256:abcd",
        "resource_limits": {
            "cpu_cores": 1.0,
            "memory_mb": 256,
            "max_pids": 16,
            "timeout_seconds": 10,
            "network_enabled": False,
        },
    }
    with pytest.raises(ContractError, match="unsupported container runner"):
        build_container_command(task_manifest, Path("/run"), Path("/out"), runner_binary="bash")


def test_critical_failure_has_frozen_weight(tmp_path: Path):
    junit_xml = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="hidden_evaluator" tests="2" failures="1" errors="0">
    <testcase name="test_normal_pass" classname="test_suite"/>
    <testcase name="test_no_data_loss" classname="test_suite">
      <failure message="Data corruption detected">AssertionError</failure>
    </testcase>
  </testsuite>
</testsuites>
"""
    xml_path = tmp_path / "junit.xml"
    xml_path.write_text(junit_xml, encoding="utf-8")

    severity_map = {
        "test_suite::test_normal_pass": "low",
        "test_suite::test_no_data_loss": "critical",
    }
    eval_rec = parse_junit(xml_path, severity_map)
    assert eval_rec.failed_weight == 8  # critical weight = 8
    assert eval_rec.total_weight == 9  # 1 (low) + 8 (critical)
    assert eval_rec.score == pytest.approx(1.0 / 9.0)


def test_skipped_junit_case_is_unscored(tmp_path: Path):
    junit_xml = """<testsuite>
  <testcase name="pass" classname="suite"/>
  <testcase name="fail" classname="suite"><failure/></testcase>
  <testcase name="skip" classname="suite"><skipped/></testcase>
</testsuite>
"""
    xml_path = tmp_path / "junit.xml"
    xml_path.write_text(junit_xml, encoding="utf-8")

    eval_rec = parse_junit(
        xml_path,
        {
            "suite::pass": "low",
            "suite::fail": "high",
            "suite::skip": "critical",
        },
    )

    assert eval_rec.passed_count == 1
    assert eval_rec.failed_count == 1
    assert eval_rec.skipped_count == 1
    assert eval_rec.total_count == 2
    assert eval_rec.total_weight == 5
    assert eval_rec.score == pytest.approx(0.2)
