"""
End-to-end and engine tests for evaluation pipeline.
"""
from pathlib import Path
from harness_eval.engine import EvaluationEngine
from harness_eval.models import Verdict
from harness_eval.runner import OfflineFixtureRunner


def test_evaluation_engine_runs_fixtures_benchmark():
    engine = EvaluationEngine(
        runner=OfflineFixtureRunner(fixtures_dir="fixtures"),
        fixtures_dir="fixtures",
    )
    base_harness = engine.load_harness_from_dir("harnesses/baseline")
    cand_harness = engine.load_harness_from_dir("harnesses/candidate_v2")
    tasks = engine.load_tasks_from_dir("benchmarks/tasks.yaml")

    assert len(tasks) == 4
    assert base_harness.name is not None
    assert cand_harness.name is not None

    report = engine.evaluate(base_harness, cand_harness, tasks)
    assert report.total_tasks == 4
    assert report.verdict == Verdict.POSITIVE
    assert report.net_quality_delta > 0
    assert len(report.task_comparisons) == 4


def test_evaluation_engine_detects_regressive_candidate():
    engine = EvaluationEngine(
        runner=OfflineFixtureRunner(fixtures_dir="fixtures"),
        fixtures_dir="fixtures",
    )
    base_harness = engine.load_harness_from_dir("harnesses/baseline")
    reg_harness = engine.load_harness_from_dir("harnesses/candidate_regressive")
    tasks = engine.load_tasks_from_dir("benchmarks/tasks.yaml")

    report = engine.evaluate(base_harness, reg_harness, tasks)
    assert report.verdict == Verdict.NEGATIVE
    assert report.regressed_tasks >= 2
