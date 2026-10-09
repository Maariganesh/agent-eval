"""
Decision and verdict engine: evaluates whether a harness change has a
positive, negative, or inconclusive impact, with concrete evidence and guardrails.
"""
from __future__ import annotations

from typing import List, Tuple
from harness_eval.models import (
    EvaluationReport,
    TaskComparison,
    TaskRunResult,
    TaskStatus,
    Verdict,
)

# Dimension Weights for Quality Score
WEIGHT_FUNCTIONAL = 0.45   # Correctness (the code works)
WEIGHT_CONVENTION = 0.25   # Conventions & team standards
WEIGHT_FULFILLMENT = 0.30  # Spec & business requirements


def compare_task_results(
    task_id: str,
    task_title: str,
    baseline: TaskRunResult,
    candidate: TaskRunResult,
) -> TaskComparison:
    """
    Compares baseline vs candidate execution for a single task.
    """
    delta_f = round(candidate.functional_score - baseline.functional_score, 3)
    delta_c = round(candidate.convention_score - baseline.convention_score, 3)
    delta_s = round(candidate.fulfillment_score - baseline.fulfillment_score, 3)
    delta_tokens = candidate.total_tokens - baseline.total_tokens
    delta_cost = round(candidate.estimated_cost_usd - baseline.estimated_cost_usd, 6)

    # Net task score delta
    net_task_delta = (
        WEIGHT_FUNCTIONAL * delta_f
        + WEIGHT_CONVENTION * delta_c
        + WEIGHT_FULFILLMENT * delta_s
    )

    evidence_notes: List[str] = []

    # Assess functional change
    if delta_f > 0:
        evidence_notes.append(
            f"Functional improvement: tests passed went from {baseline.tests_passed}/{baseline.tests_total} to {candidate.tests_passed}/{candidate.tests_total} (+{delta_f*100:.1f}%)"
        )
    elif delta_f < 0:
        evidence_notes.append(
            f"CRITICAL FUNCTIONAL REGRESSION: tests passed dropped from {baseline.tests_passed}/{baseline.tests_total} to {candidate.tests_passed}/{candidate.tests_total} ({delta_f*100:.1f}%)"
        )

    # Assess convention change
    if delta_c > 0:
        evidence_notes.append(
            f"Convention adherence improved: violations reduced from {len(baseline.convention_violations)} to {len(candidate.convention_violations)} (+{delta_c*100:.1f}%)"
        )
    elif delta_c < 0:
        evidence_notes.append(
            f"Convention regression: violations increased by {len(candidate.convention_violations) - len(baseline.convention_violations)} ({delta_c*100:.1f}%)"
        )

    # Assess spec fulfillment change
    if delta_s > 0:
        evidence_notes.append(f"Spec fulfillment improved (+{delta_s*100:.1f}%)")
    elif delta_s < 0:
        evidence_notes.append(f"Spec fulfillment dropped ({delta_s*100:.1f}%)")

    # Assess cost & tokens
    if delta_tokens > 0:
        pct_cost = (delta_tokens / baseline.total_tokens * 100) if baseline.total_tokens > 0 else 0
        evidence_notes.append(f"Token overhead increased by {delta_tokens:,} tokens (+{pct_cost:.1f}%)")
    elif delta_tokens < 0:
        evidence_notes.append(f"Token efficiency improved by {abs(delta_tokens):,} tokens")

    # Classify status
    if delta_f < -0.05 or delta_c < -0.15 or delta_s < -0.15:
        status = TaskStatus.REGRESSED
        summary = "Regressed: Critical metrics degraded"
    elif net_task_delta >= 0.05:
        status = TaskStatus.IMPROVED
        summary = "Improved: Measurable quality gains observed"
    elif net_task_delta <= -0.05:
        status = TaskStatus.REGRESSED
        summary = "Regressed: Net quality degraded"
    elif abs(net_task_delta) < 0.05 and (abs(delta_tokens) > 500):
        status = TaskStatus.MIXED
        summary = "Mixed: Quality unchanged but token efficiency altered"
    else:
        status = TaskStatus.UNCHANGED
        summary = "Unchanged: Baseline and candidate performed equally"

    return TaskComparison(
        task_id=task_id,
        task_title=task_title,
        status=status,
        baseline=baseline,
        candidate=candidate,
        delta_functional=delta_f,
        delta_convention=delta_c,
        delta_fulfillment=delta_s,
        delta_total_tokens=delta_tokens,
        delta_cost_usd=delta_cost,
        change_summary=summary,
        evidence_notes=evidence_notes,
    )


def compute_verdict(
    comparisons: List[TaskComparison],
    baseline_name: str,
    candidate_name: str,
) -> Tuple[Verdict, str, List[str], List[str]]:
    """
    Synthesizes overall verdict, reasons, and actionable recommendations.
    """
    total = len(comparisons)
    if total == 0:
        return Verdict.INCONCLUSIVE, "No tasks were evaluated.", [], []

    improved_count = sum(1 for c in comparisons if c.status == TaskStatus.IMPROVED)
    regressed_count = sum(1 for c in comparisons if c.status == TaskStatus.REGRESSED)
    unchanged_count = total - improved_count - regressed_count

    avg_delta_f = sum(c.delta_functional for c in comparisons) / total
    avg_delta_c = sum(c.delta_convention for c in comparisons) / total
    avg_delta_s = sum(c.delta_fulfillment for c in comparisons) / total

    net_quality_delta = (
        WEIGHT_FUNCTIONAL * avg_delta_f
        + WEIGHT_CONVENTION * avg_delta_c
        + WEIGHT_FULFILLMENT * avg_delta_s
    ) * 100

    base_tokens = sum(c.baseline.total_tokens for c in comparisons)
    cand_tokens = sum(c.candidate.total_tokens for c in comparisons)
    cost_pct_change = ((cand_tokens - base_tokens) / base_tokens * 100) if base_tokens > 0 else 0.0

    reasons: List[str] = []
    recommendations: List[str] = []

    # Check for functional regressions
    hard_functional_regressions = [
        c for c in comparisons if c.delta_functional < -0.05
    ]

    if hard_functional_regressions:
        reasons.append(
            f"GUARDRAIL VIOLATED: Candidate regressed functional correctness on {len(hard_functional_regressions)} task(s): "
            + ", ".join(f"'{c.task_title}' ({c.delta_functional*100:+.0f}%)" for c in hard_functional_regressions)
        )

    if avg_delta_f > 0.05:
        reasons.append(
            f"Functional correctness improved across tasks by {avg_delta_f*100:+.1f}%"
        )
    elif avg_delta_f < -0.05:
        reasons.append(
            f"Average test pass rate dropped by {avg_delta_f*100:.1f}%"
        )

    if avg_delta_c > 0.05:
        reasons.append(
            f"Team convention & architectural rule compliance improved by {avg_delta_c*100:+.1f}%"
        )
    elif avg_delta_c < -0.05:
        reasons.append(
            f"Team convention compliance declined by {avg_delta_c*100:.1f}%"
        )

    if avg_delta_s > 0.05:
        reasons.append(
            f"Business specification fulfillment improved by {avg_delta_s*100:+.1f}%"
        )
    elif avg_delta_s < -0.05:
        reasons.append(
            f"Business specification fulfillment dropped by {avg_delta_s*100:.1f}%"
        )

    # Cost / Token impact
    if cost_pct_change > 50:
        reasons.append(
            f"Significant token overhead: candidate consumes +{cost_pct_change:.1f}% more tokens ({cand_tokens - base_tokens:,} additional tokens)"
        )
    elif cost_pct_change < -10:
        reasons.append(
            f"Token efficiency improved: candidate saves {abs(cost_pct_change):.1f}% tokens"
        )

    # Decision Matrix
    if hard_functional_regressions or avg_delta_f < -0.05 or net_quality_delta < -3.0:
        verdict = Verdict.NEGATIVE
        summary = f"NEGATIVE IMPACT: Harness '{candidate_name}' introduces regressions and should NOT be deployed."
        recommendations.append("Do NOT roll out this harness change to engineering teams.")
        recommendations.append("Investigate broken test cases in regressed tasks before iterating on prompt/rules.")
        if cost_pct_change > 40:
            recommendations.append("Prune redundant instructions to reduce token waste.")

    elif cost_pct_change > 60 and net_quality_delta < 5.0:
        verdict = Verdict.NEGATIVE
        summary = f"NEGATIVE IMPACT: Excessive token bloat (+{cost_pct_change:.1f}%) without sufficient quality gain."
        recommendations.append("Reject change: The minor quality gain does not justify the massive token cost.")

    elif net_quality_delta >= 5.0 and len(hard_functional_regressions) == 0:
        verdict = Verdict.POSITIVE
        summary = f"POSITIVE IMPACT: Harness '{candidate_name}' reliably boosts quality (+{net_quality_delta:.1f} net pts) with zero correctness regressions."
        recommendations.append("SAFE TO SHIP: Roll out candidate harness to the engineering team.")
        recommendations.append(f"Monitor production token budgets (+{cost_pct_change:+.1f}% token variance).")

    else:
        verdict = Verdict.INCONCLUSIVE
        summary = f"INCONCLUSIVE: Harness '{candidate_name}' does not show statistically decisive net benefit."
        recommendations.append("Gather more benchmark tasks before making a deployment decision.")
        recommendations.append("Refine candidate instructions to specifically target failing rubrics.")

    return verdict, summary, reasons, recommendations
