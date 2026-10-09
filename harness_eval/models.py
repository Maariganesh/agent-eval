"""
Core domain models for the Agent Harness Evaluation framework.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Verdict(str, Enum):
    POSITIVE = "POSITIVE"      # Clear improvement across key dimensions without critical regressions
    NEGATIVE = "NEGATIVE"      # Regressions detected in correctness or heavy cost blowup
    INCONCLUSIVE = "INCONCLUSIVE"  # Mixed or statistically marginal results


class TaskStatus(str, Enum):
    IMPROVED = "IMPROVED"
    REGRESSED = "REGRESSED"
    UNCHANGED = "UNCHANGED"
    MIXED = "MIXED"


class RubricCriterion(BaseModel):
    id: str
    description: str
    weight: float = 1.0
    type: str = "ast"  # "ast", "regex", "test", "llm_judge"
    rule_spec: Dict[str, Any] = Field(default_factory=dict)


class EvalTask(BaseModel):
    id: str
    title: str
    description: str
    category: str = "general"
    starter_code: Dict[str, str] = Field(default_factory=dict)  # relative path -> content
    test_suite_code: Dict[str, str] = Field(default_factory=dict)  # relative path -> test file content
    test_command: str = "pytest"
    expected_files: List[str] = Field(default_factory=list)
    conventions: List[Dict[str, Any]] = Field(default_factory=list)
    rubric: List[RubricCriterion] = Field(default_factory=list)
    token_budget: int = 4000


class HarnessConfig(BaseModel):
    name: str
    description: str = ""
    system_prompt: str = ""
    agents_md: str = ""
    rules: Dict[str, str] = Field(default_factory=dict)  # filename -> rule content
    skills: Dict[str, str] = Field(default_factory=dict)  # skill_name -> skill content
    model: str = "gpt-4o"
    temperature: float = 0.2


class RubricScore(BaseModel):
    criterion_id: str
    description: str
    passed: bool
    score: float
    weight: float
    details: str = ""


class TaskRunResult(BaseModel):
    task_id: str
    task_title: str
    harness_name: str
    success: bool
    
    # 1. The code works (Functional)
    functional_score: float  # 0.0 to 1.0
    tests_passed: int
    tests_total: int
    test_output: str = ""
    
    # 2. It follows team's conventions (Convention)
    convention_score: float  # 0.0 to 1.0
    convention_violations: List[str] = Field(default_factory=list)
    convention_details: Dict[str, Any] = Field(default_factory=dict)
    
    # 3. It does what the business asked (Fulfillment)
    fulfillment_score: float  # 0.0 to 1.0
    rubric_scores: List[RubricScore] = Field(default_factory=list)
    
    # 4. It did not cost a fortune (Cost & Efficiency)
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    duration_seconds: float = 0.0
    
    # Generated code artifacts
    generated_files: Dict[str, str] = Field(default_factory=dict)
    error_message: Optional[str] = None


class TaskComparison(BaseModel):
    task_id: str
    task_title: str
    status: TaskStatus
    
    baseline: TaskRunResult
    candidate: TaskRunResult
    
    delta_functional: float   # candidate - baseline
    delta_convention: float
    delta_fulfillment: float
    delta_total_tokens: int
    delta_cost_usd: float
    
    change_summary: str
    evidence_notes: List[str] = Field(default_factory=list)


class EvaluationReport(BaseModel):
    timestamp: str
    baseline_name: str
    candidate_name: str
    total_tasks: int
    
    # Aggregates Baseline
    baseline_avg_functional: float
    baseline_avg_convention: float
    baseline_avg_fulfillment: float
    baseline_total_cost_usd: float
    baseline_total_tokens: int
    
    # Aggregates Candidate
    candidate_avg_functional: float
    candidate_avg_convention: float
    candidate_avg_fulfillment: float
    candidate_total_cost_usd: float
    candidate_total_tokens: int
    
    # Deltas
    net_functional_delta: float
    net_convention_delta: float
    net_fulfillment_delta: float
    net_quality_delta: float
    net_cost_pct_change: float
    
    # Task Counts
    improved_tasks: int
    regressed_tasks: int
    unchanged_tasks: int
    
    # Verdict & Decision Engine
    verdict: Verdict
    verdict_summary: str
    verdict_reasons: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    # Detailed Comparisons
    task_comparisons: List[TaskComparison] = Field(default_factory=list)
