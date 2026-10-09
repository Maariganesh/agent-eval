"""
Markdown report generator: creates exportable summaries for pull requests,
CI/CD job summaries, and documentation.
"""
from __future__ import annotations

from harness_eval.models import EvaluationReport, TaskStatus, Verdict


def generate_markdown_report(report: EvaluationReport) -> str:
    """
    Renders the evaluation report as GitHub-flavored Markdown.
    """
    badge_color = "brightgreen" if report.verdict == Verdict.POSITIVE else "red" if report.verdict == Verdict.NEGATIVE else "yellow"
    
    lines = [
        f"# Agent Harness Evaluation Report",
        f"",
        f"**Verdict:** `[{report.verdict.value}]` &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"**Baseline:** `{report.baseline_name}` &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"**Candidate:** `{report.candidate_name}` &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"**Timestamp:** `{report.timestamp}`",
        f"",
        f"## Executive Summary",
        f"",
        f"> **{report.verdict_summary}**",
        f"",
    ]

    if report.verdict_reasons:
        lines.append("### Evidence & Reasoning")
        for r in report.verdict_reasons:
            lines.append(f"- {r}")
        lines.append("")

    # High-level Metrics Table
    lines.extend([
        "## Overall Metrics Comparison",
        "",
        "| Evaluation Dimension | Baseline | Candidate | Net Delta |",
        "| :--- | :---: | :---: | :---: |",
        f"| **1. Functional Correctness (Tests)** | {report.baseline_avg_functional*100:.1f}% | {report.candidate_avg_functional*100:.1f}% | `{report.net_functional_delta*100:+.1f}%` |",
        f"| **2. Team Convention Compliance** | {report.baseline_avg_convention*100:.1f}% | {report.candidate_avg_convention*100:.1f}% | `{report.net_convention_delta*100:+.1f}%` |",
        f"| **3. Business Spec Fulfillment** | {report.baseline_avg_fulfillment*100:.1f}% | {report.candidate_avg_fulfillment*100:.1f}% | `{report.net_fulfillment_delta*100:+.1f}%` |",
        f"| **Net Quality Score** | — | — | **`{report.net_quality_delta:+.1f} pts`** |",
        f"| **4. Token Usage & Cost** | {report.baseline_total_tokens:,} toks (${report.baseline_total_cost_usd:.4f}) | {report.candidate_total_tokens:,} toks (${report.candidate_total_cost_usd:.4f}) | `{report.net_cost_pct_change:+.1f}%` |",
        "",
    ])

    # Task Breakdown Table
    lines.extend([
        "## Task-by-Task Evidence Matrix",
        "",
        "| Task ID | Status | Func Δ | Conv Δ | Spec Δ | Tokens Δ | Summary |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :--- |",
    ])

    for cmp in report.task_comparisons:
        status_md = (
            "✅ **IMPROVED**" if cmp.status == TaskStatus.IMPROVED
            else "❌ **REGRESSED**" if cmp.status == TaskStatus.REGRESSED
            else "⚠️ **MIXED**" if cmp.status == TaskStatus.MIXED
            else "➖ UNCHANGED"
        )
        lines.append(
            f"| `{cmp.task_id}` | {status_md} | {cmp.delta_functional*100:+.1f}% | "
            f"{cmp.delta_convention*100:+.1f}% | {cmp.delta_fulfillment*100:+.1f}% | "
            f"{cmp.delta_total_tokens:+,} | {cmp.change_summary} |"
        )
    lines.append("")

    # Detailed Task Breakdown
    lines.append("## Detailed Task Drilldown")
    for cmp in report.task_comparisons:
        lines.extend([
            f"### `{cmp.task_id}`: {cmp.task_title}",
            f"- **Status:** `{cmp.status.value}`",
            f"- **Baseline:** Tests {cmp.baseline.tests_passed}/{cmp.baseline.tests_total} ({cmp.baseline.functional_score*100:.0f}%), Conventions {cmp.baseline.convention_score*100:.0f}%, Tokens {cmp.baseline.total_tokens:,}",
            f"- **Candidate:** Tests {cmp.candidate.tests_passed}/{cmp.candidate.tests_total} ({cmp.candidate.functional_score*100:.0f}%), Conventions {cmp.candidate.convention_score*100:.0f}%, Tokens {cmp.candidate.total_tokens:,}",
        ])
        if cmp.evidence_notes:
            lines.append("- **Notes:**")
            for note in cmp.evidence_notes:
                lines.append(f"  - {note}")
        if cmp.candidate.convention_violations:
            lines.append("- **Candidate Convention Violations:**")
            for v in cmp.candidate.convention_violations:
                lines.append(f"  - `{v}`")
        lines.append("")

    # Recommendations
    if report.recommendations:
        lines.extend([
            "## Recommendations for Harness Maintainer",
            "",
        ])
        for rec in report.recommendations:
            lines.append(f"- 💡 {rec}")
        lines.append("")

    return "\n".join(lines)
