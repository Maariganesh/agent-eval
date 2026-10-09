"""
Unit tests for verdict determination and guardrails.
"""
from harness_eval.models import TaskRunResult, TaskStatus, Verdict
from harness_eval.verdict import compare_task_results, compute_verdict


def _make_result(
    harness: str,
    func: float,
    conv: float,
    fulf: float,
    tokens: int,
    passed: int = 4,
    total: int = 4,
) -> TaskRunResult:
    return TaskRunResult(
        task_id="t1",
        task_title="Test Task",
        harness_name=harness,
        success=(func >= 1.0),
        functional_score=func,
        tests_passed=passed,
        tests_total=total,
        convention_score=conv,
        fulfillment_score=fulf,
        total_tokens=tokens,
        input_tokens=int(tokens * 0.7),
        output_tokens=int(tokens * 0.3),
        estimated_cost_usd=0.01,
        duration_seconds=1.0,
    )


def test_compare_task_results_improved():
    base = _make_result("base", 0.5, 0.5, 0.5, 1000, 2, 4)
    cand = _make_result("cand", 1.0, 1.0, 1.0, 1200, 4, 4)
    cmp = compare_task_results("t1", "Test Task", base, cand)
    assert cmp.status == TaskStatus.IMPROVED
    assert cmp.delta_functional == 0.5


def test_compare_task_results_regressed():
    base = _make_result("base", 1.0, 1.0, 1.0, 1000, 4, 4)
    cand = _make_result("cand", 0.5, 0.5, 0.5, 1200, 2, 4)
    cmp = compare_task_results("t1", "Test Task", base, cand)
    assert cmp.status == TaskStatus.REGRESSED


def test_verdict_positive_when_quality_rises_without_regressions():
    base = _make_result("base", 0.6, 0.6, 0.6, 1000, 3, 5)
    cand = _make_result("cand", 1.0, 0.9, 0.9, 1300, 5, 5)
    cmp = compare_task_results("t1", "Task 1", base, cand)
    verdict, summary, reasons, recs = compute_verdict([cmp], "base", "cand")
    assert verdict == Verdict.POSITIVE
    assert "POSITIVE IMPACT" in summary


def test_verdict_negative_when_functional_regression_occurs():
    base = _make_result("base", 1.0, 0.8, 0.8, 1000, 5, 5)
    cand = _make_result("cand", 0.6, 0.9, 0.9, 1100, 3, 5)  # tests dropped!
    cmp = compare_task_results("t1", "Task 1", base, cand)
    verdict, summary, reasons, recs = compute_verdict([cmp], "base", "cand")
    assert verdict == Verdict.NEGATIVE
    assert any("GUARDRAIL VIOLATED" in r for r in reasons)
