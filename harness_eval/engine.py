"""
Evaluation engine: orchestrates the execution of baseline vs candidate harnesses
across benchmark tasks, collects dimensional metrics, and compiles the final report.
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Dict, List, Optional
import yaml

from harness_eval.metrics.functional import evaluate_functional
from harness_eval.metrics.convention import ConventionChecker
from harness_eval.metrics.fulfillment import FulfillmentEvaluator
from harness_eval.metrics.cost import calculate_cost, count_tokens
from harness_eval.models import (
    EvalTask,
    EvaluationReport,
    HarnessConfig,
    RubricCriterion,
    TaskComparison,
    TaskRunResult,
    Verdict,
)
from harness_eval.runner import AgentRunner, OfflineFixtureRunner
from harness_eval.verdict import compare_task_results, compute_verdict


class EvaluationEngine:
    """
    Main evaluation pipeline orchestrator.
    """

    def __init__(
        self,
        runner: Optional[AgentRunner] = None,
        fixtures_dir: Path | str = "fixtures",
    ):
        self.runner = runner or OfflineFixtureRunner(fixtures_dir=fixtures_dir)

    def load_harness_from_dir(self, harness_dir: Path | str) -> HarnessConfig:
        """
        Parses harness files (AGENTS.md, rules/, skills/, harness.yaml).
        """
        h_path = Path(harness_dir)
        name = h_path.name
        description = ""
        system_prompt = ""
        agents_md = ""
        rules: Dict[str, str] = {}
        skills: Dict[str, str] = {}
        model = "gpt-4o"
        temperature = 0.2

        # Check for config file
        cfg_file = h_path / "harness.yaml"
        if cfg_file.exists():
            try:
                data = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
                name = data.get("name", name)
                description = data.get("description", "")
                model = data.get("model", model)
                temperature = data.get("temperature", temperature)
            except Exception:
                pass

        # Check for AGENTS.md
        agents_file = h_path / "AGENTS.md"
        if agents_file.exists():
            agents_md = agents_file.read_text(encoding="utf-8")

        # Check for system prompt file
        sys_file = h_path / "system_prompt.txt"
        if sys_file.exists():
            system_prompt = sys_file.read_text(encoding="utf-8")

        # Load rules directory
        rules_dir = h_path / "rules"
        if rules_dir.is_dir():
            for rf in rules_dir.glob("*.md"):
                rules[rf.name] = rf.read_text(encoding="utf-8")

        # Load skills directory
        skills_dir = h_path / "skills"
        if skills_dir.is_dir():
            for sf in skills_dir.glob("**/*"):
                if sf.is_file() and (sf.suffix in (".md", ".txt", ".json")):
                    rel_s = sf.relative_to(skills_dir).as_posix()
                    skills[rel_s] = sf.read_text(encoding="utf-8")

        return HarnessConfig(
            name=name,
            description=description,
            system_prompt=system_prompt,
            agents_md=agents_md,
            rules=rules,
            skills=skills,
            model=model,
            temperature=temperature,
        )

    def load_tasks_from_dir(self, tasks_path: Path | str) -> List[EvalTask]:
        """
        Loads tasks from a tasks.yaml or a benchmark directory.
        """
        path = Path(tasks_path)
        tasks: List[EvalTask] = []

        if path.is_file() and path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
            task_list = data if isinstance(data, list) else data.get("tasks", [])
            for t_data in task_list:
                rubric_objs = [
                    RubricCriterion(**r) for r in t_data.get("rubric", [])
                ]
                task = EvalTask(
                    id=t_data["id"],
                    title=t_data["title"],
                    description=t_data["description"],
                    category=t_data.get("category", "general"),
                    starter_code=t_data.get("starter_code", {}),
                    test_suite_code=t_data.get("test_suite_code", {}),
                    test_command=t_data.get("test_command", "pytest"),
                    expected_files=t_data.get("expected_files", []),
                    conventions=t_data.get("conventions", []),
                    rubric=rubric_objs,
                    token_budget=t_data.get("token_budget", 4000),
                )
                tasks.append(task)
            return tasks

        # If it's a directory containing task subfolders
        yaml_file = path / "tasks.yaml"
        if yaml_file.exists():
            return self.load_tasks_from_dir(yaml_file)

        return tasks

    def evaluate_harness_on_task(
        self,
        task: EvalTask,
        harness: HarnessConfig,
    ) -> TaskRunResult:
        """
        Runs and evaluates a single task under a specific harness.
        """
        # 1. Execute agent runner
        generated_files, in_tok, out_tok, dur, err = self.runner.run_task(task, harness)
        total_tok = in_tok + out_tok
        cost, _ = calculate_cost(in_tok, out_tok, model=harness.model)

        if err or not generated_files:
            return TaskRunResult(
                task_id=task.id,
                task_title=task.title,
                harness_name=harness.name,
                success=False,
                functional_score=0.0,
                tests_passed=0,
                tests_total=1,
                test_output=err or "No files generated by agent",
                convention_score=0.0,
                convention_violations=[err or "No code generated"],
                fulfillment_score=0.0,
                input_tokens=in_tok,
                output_tokens=out_tok,
                total_tokens=total_tok,
                estimated_cost_usd=cost,
                duration_seconds=dur,
                generated_files=generated_files,
                error_message=err,
            )

        # 2. Evaluate functional correctness (test execution)
        func_score, passed_tests, total_tests, test_out = evaluate_functional(
            code_files=generated_files,
            test_files=task.test_suite_code,
            test_command=task.test_command,
        )

        # 3. Evaluate conventions
        checker = ConventionChecker(conventions=task.conventions)
        conv_score, violations, conv_details = checker.evaluate_code(generated_files)

        # 4. Evaluate specification fulfillment
        fulfill_eval = FulfillmentEvaluator(rubric=task.rubric)
        fulf_score, rubric_scores = fulfill_eval.evaluate(generated_files)

        return TaskRunResult(
            task_id=task.id,
            task_title=task.title,
            harness_name=harness.name,
            success=(func_score >= 1.0 and len(violations) == 0),
            functional_score=func_score,
            tests_passed=passed_tests,
            tests_total=total_tests,
            test_output=test_out,
            convention_score=conv_score,
            convention_violations=violations,
            convention_details=conv_details,
            fulfillment_score=fulf_score,
            rubric_scores=rubric_scores,
            input_tokens=in_tok,
            output_tokens=out_tok,
            total_tokens=total_tok,
            estimated_cost_usd=cost,
            duration_seconds=dur,
            generated_files=generated_files,
            error_message=None,
        )

    def evaluate(
        self,
        baseline_harness: HarnessConfig,
        candidate_harness: HarnessConfig,
        tasks: List[EvalTask],
    ) -> EvaluationReport:
        """
        Runs comprehensive comparative evaluation across all tasks.
        """
        comparisons: List[TaskComparison] = []

        for task in tasks:
            base_result = self.evaluate_harness_on_task(task, baseline_harness)
            cand_result = self.evaluate_harness_on_task(task, candidate_harness)
            cmp = compare_task_results(task.id, task.title, base_result, cand_result)
            comparisons.append(cmp)

        num_tasks = len(tasks)
        if num_tasks == 0:
            raise ValueError("Evaluation requires at least one task.")

        # Aggregates Baseline
        base_avg_f = sum(c.baseline.functional_score for c in comparisons) / num_tasks
        base_avg_c = sum(c.baseline.convention_score for c in comparisons) / num_tasks
        base_avg_s = sum(c.baseline.fulfillment_score for c in comparisons) / num_tasks
        base_total_cost = sum(c.baseline.estimated_cost_usd for c in comparisons)
        base_total_tokens = sum(c.baseline.total_tokens for c in comparisons)

        # Aggregates Candidate
        cand_avg_f = sum(c.candidate.functional_score for c in comparisons) / num_tasks
        cand_avg_c = sum(c.candidate.convention_score for c in comparisons) / num_tasks
        cand_avg_s = sum(c.candidate.fulfillment_score for c in comparisons) / num_tasks
        cand_total_cost = sum(c.candidate.estimated_cost_usd for c in comparisons)
        cand_total_tokens = sum(c.candidate.total_tokens for c in comparisons)

        # Deltas
        net_f_delta = round(cand_avg_f - base_avg_f, 3)
        net_c_delta = round(cand_avg_c - base_avg_c, 3)
        net_s_delta = round(cand_avg_s - base_avg_s, 3)
        net_quality_delta = round(
            (0.45 * net_f_delta + 0.25 * net_c_delta + 0.30 * net_s_delta) * 100, 1
        )
        cost_pct_change = round(
            ((cand_total_tokens - base_total_tokens) / base_total_tokens * 100)
            if base_total_tokens > 0 else 0.0, 1
        )

        verdict, summary, reasons, recs = compute_verdict(
            comparisons, baseline_harness.name, candidate_harness.name
        )

        improved = sum(1 for c in comparisons if c.status.value == "IMPROVED")
        regressed = sum(1 for c in comparisons if c.status.value == "REGRESSED")
        unchanged = num_tasks - improved - regressed

        return EvaluationReport(
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            baseline_name=baseline_harness.name,
            candidate_name=candidate_harness.name,
            total_tasks=num_tasks,
            baseline_avg_functional=round(base_avg_f, 3),
            baseline_avg_convention=round(base_avg_c, 3),
            baseline_avg_fulfillment=round(base_avg_s, 3),
            baseline_total_cost_usd=round(base_total_cost, 6),
            baseline_total_tokens=base_total_tokens,
            candidate_avg_functional=round(cand_avg_f, 3),
            candidate_avg_convention=round(cand_avg_c, 3),
            candidate_avg_fulfillment=round(cand_avg_s, 3),
            candidate_total_cost_usd=round(cand_total_cost, 6),
            candidate_total_tokens=cand_total_tokens,
            net_functional_delta=net_f_delta,
            net_convention_delta=net_c_delta,
            net_fulfillment_delta=net_s_delta,
            net_quality_delta=net_quality_delta,
            net_cost_pct_change=cost_pct_change,
            improved_tasks=improved,
            regressed_tasks=regressed,
            unchanged_tasks=unchanged,
            verdict=verdict,
            verdict_summary=summary,
            verdict_reasons=reasons,
            recommendations=recs,
            task_comparisons=comparisons,
        )
