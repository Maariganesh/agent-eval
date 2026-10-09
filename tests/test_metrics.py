"""
Unit tests for metric evaluators (functional, convention, fulfillment, cost).
"""
import pytest
from harness_eval.metrics.functional import evaluate_functional, _parse_pytest_output
from harness_eval.metrics.convention import ConventionChecker
from harness_eval.metrics.fulfillment import FulfillmentEvaluator
from harness_eval.metrics.cost import calculate_cost, count_tokens
from harness_eval.models import RubricCriterion


def test_parse_pytest_output():
    sample_out = "=== 3 passed, 1 failed in 0.20s ==="
    passed, total = _parse_pytest_output(sample_out)
    assert passed == 3
    assert total == 4

    sample_out_clean = "=== 5 passed in 0.05s ==="
    passed, total = _parse_pytest_output(sample_out_clean)
    assert passed == 5
    assert total == 5


def test_convention_checker_detects_missing_types_and_bare_except():
    code_bad = """
def calculate(a, b):
    try:
        return a / b
    except:
        pass
"""
    checker = ConventionChecker()
    score, violations, details = checker.evaluate_code({"math_ops.py": code_bad})
    assert score < 1.0
    assert any("type annotation" in v for v in violations)
    assert any("Bare 'except:'" in v for v in violations)


def test_convention_checker_passes_compliant_code():
    code_good = """
def add_numbers(a: int, b: int) -> int:
    \"\"\"Adds two numbers together.\"\"\"
    return a + b
"""
    checker = ConventionChecker()
    score, violations, details = checker.evaluate_code({"clean.py": code_good})
    assert score == 1.0
    assert len(violations) == 0


def test_convention_checker_sql_injection():
    unsafe_code = """
def get_user(db, user_id: str) -> None:
    \"\"\"Query user.\"\"\"
    db.execute(f"SELECT * FROM users WHERE id = '{user_id}'")
"""
    checker = ConventionChecker(conventions=[{"name": "sql", "type": "no_sql_formatting"}])
    score, violations, _ = checker.evaluate_code({"db.py": unsafe_code})
    assert any("SQL Injection vulnerability" in v for v in violations)


def test_fulfillment_rubric_evaluator():
    rubric = [
        RubricCriterion(
            id="has_lock",
            description="Uses threading lock",
            weight=1.0,
            type="regex",
            rule_spec={"pattern": "threading\\.Lock\\(\\)|\bLock\b"},
        ),
        RubricCriterion(
            id="has_method",
            description="Implements process method",
            weight=2.0,
            type="ast_class_method",
            rule_spec={"class_name": "Worker", "method_name": "process"},
        ),
    ]
    evaluator = FulfillmentEvaluator(rubric=rubric)

    code = """
import threading

class Worker:
    def __init__(self):
        self.lock = threading.Lock()
    def process(self):
        return True
"""
    score, results = evaluator.evaluate({"worker.py": code})
    assert score == 1.0
    assert len(results) == 2
    assert all(r.passed for r in results)


def test_cost_calculation():
    cost, total_tok = calculate_cost(input_tokens=1000, output_tokens=500, model="gpt-4o")
    assert total_tok == 1500
    assert cost > 0
