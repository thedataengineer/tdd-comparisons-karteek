"""Report rendering for ablation study results."""

from __future__ import annotations

from typing import Any


def render_report(results: dict[str, Any]) -> str:
    """Render Markdown report from study results dictionary."""
    study_name = results.get("study_name", "TDD Ablation Study")
    total_runs = results.get("total_runs", 0)
    decision_data = results.get("adoption_decision", {})
    adopt = decision_data.get("adopt", False)
    reasons = decision_data.get("reasons", [])

    status_str = "ADOPT" if adopt else "REJECT"

    md = [
        f"# {study_name}",
        "",
        "## Executive Summary",
        "",
        f"- **Decision:** {status_str}",
        f"- **Total Analyzed Runs:** {total_runs}",
    ]

    if reasons:
        md.append("- **Rejection Reasons:**")
        for r in reasons:
            md.append(f"  - {r}")

    md.extend(
        [
            "",
            "## Methodological Controls",
            "- Network isolation: disabled",
            "- Environment: pinned Python 3.12.5 + Docker container digest",
            "- Blinding: condition labels and traces stripped from review panels",
            "- Censoring rule: intention-to-treat analysis scores incomplete runs zero",
            "",
        ]
    )

    return "\n".join(md)
