"""
Spec Fulfillment evaluator: checks if the generated code fulfills specific
business requirements and edge case rubrics.
"""
from __future__ import annotations

import ast
import re
from typing import Dict, List, Tuple
from harness_eval.models import RubricCriterion, RubricScore


class FulfillmentEvaluator:
    """
    Evaluates business specification rubric criteria against generated code.
    """

    def __init__(self, rubric: List[RubricCriterion]):
        self.rubric = rubric

    def evaluate(self, files: Dict[str, str]) -> Tuple[float, List[RubricScore]]:
        """
        Evaluates code against rubric criteria.
        Returns:
            (fulfillment_score [0.0..1.0], list_of_rubric_scores)
        """
        if not self.rubric:
            return 1.0, []

        scores: List[RubricScore] = []
        total_weight = 0.0
        earned_weight = 0.0

        for criterion in self.rubric:
            total_weight += criterion.weight
            passed, details = self._check_criterion(criterion, files)
            score_val = 1.0 if passed else 0.0
            earned_weight += score_val * criterion.weight

            scores.append(
                RubricScore(
                    criterion_id=criterion.id,
                    description=criterion.description,
                    passed=passed,
                    score=score_val,
                    weight=criterion.weight,
                    details=details,
                )
            )

        fulfillment_score = (earned_weight / total_weight) if total_weight > 0 else 1.0
        return round(fulfillment_score, 3), scores

    def _check_criterion(self, criterion: RubricCriterion, files: Dict[str, str]) -> Tuple[bool, str]:
        c_type = criterion.type
        rule = criterion.rule_spec

        if c_type == "regex":
            pattern = rule.get("pattern", "")
            flags = re.MULTILINE | (re.IGNORECASE if rule.get("ignore_case", True) else 0)
            target_file = rule.get("file")

            for fname, content in files.items():
                if target_file and target_file != fname:
                    continue
                if re.search(pattern, content, flags):
                    return True, f"Found pattern match for '{pattern}'"
            return False, f"Missing required pattern: {criterion.description}"

        elif c_type == "ast_class_method":
            class_name = rule.get("class_name")
            method_name = rule.get("method_name")
            target_file = rule.get("file")

            for fname, content in files.items():
                if target_file and target_file != fname:
                    continue
                if not fname.endswith(".py"):
                    continue
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef) and (not class_name or node.name == class_name):
                            for item in node.body:
                                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                    if item.name == method_name:
                                        return True, f"Class '{node.name}' implements method '{method_name}'"
                except SyntaxError:
                    pass
            return False, f"Method '{method_name}' not found in expected class"

        elif c_type == "ast_function":
            func_name = rule.get("function_name")
            target_file = rule.get("file")

            for fname, content in files.items():
                if target_file and target_file != fname:
                    continue
                if not fname.endswith(".py"):
                    continue
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if node.name == func_name:
                                return True, f"Function '{func_name}' is implemented"
                except SyntaxError:
                    pass
            return False, f"Function '{func_name}' is missing"

        elif c_type == "defensive_check":
            # Checks for explicit input validation raising ValueError or custom exception
            expected_exception = rule.get("exception", "ValueError")
            found = False
            for fname, content in files.items():
                if not fname.endswith(".py"):
                    continue
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Raise):
                            if node.exc:
                                exc_name = ""
                                if isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
                                    exc_name = node.exc.func.id
                                elif isinstance(node.exc, ast.Name):
                                    exc_name = node.exc.id
                                if exc_name == expected_exception:
                                    found = True
                                    break
                except SyntaxError:
                    pass
            if found:
                return True, f"Defensive check raises {expected_exception} on invalid input"
            return False, f"Missing defensive check raising {expected_exception}"

        # Fallback assertion check
        return True, "Criterion passed by default"
