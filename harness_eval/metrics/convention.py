"""
Convention evaluator: checks code conventions, typing, error handling,
security rules, and team standards using AST and static analysis.
"""
from __future__ import annotations

import ast
import re
from typing import Any, Dict, List, Tuple


class ConventionChecker:
    """
    Evaluates compliance with engineering team conventions.
    """

    def __init__(self, conventions: List[Dict[str, Any]] | None = None):
        self.conventions = conventions or []

    def evaluate_code(self, files: Dict[str, str]) -> Tuple[float, List[str], Dict[str, Any]]:
        """
        Evaluates conventions across all supplied code files.
        Returns:
            (convention_score [0.0..1.0], violations_list, details_dict)
        """
        violations: List[str] = []
        checks_performed = 0
        checks_passed = 0

        for filename, content in files.items():
            if not filename.endswith(".py"):
                continue

            try:
                tree = ast.parse(content, filename=filename)
            except SyntaxError as e:
                violations.append(f"[{filename}:{e.lineno}] SyntaxError prevents convention check: {e.msg}")
                checks_performed += 1
                continue

            # Standard convention 1: Type annotations on public functions
            checks_performed += 1
            missing_types = self._check_type_annotations(tree, filename)
            if missing_types:
                violations.extend(missing_types)
            else:
                checks_passed += 1

            # Standard convention 2: Proper exception handling (no bare except, no pass in except)
            checks_performed += 1
            bad_excepts = self._check_exception_handling(tree, filename)
            if bad_excepts:
                violations.extend(bad_excepts)
            else:
                checks_passed += 1

            # Standard convention 3: Docstrings on classes and public functions
            checks_performed += 1
            missing_docs = self._check_docstrings(tree, filename)
            if missing_docs:
                violations.extend(missing_docs)
            else:
                checks_passed += 1

            # Standard convention 4: No print statements in production code (use logging)
            checks_performed += 1
            print_uses = self._check_no_print(tree, filename)
            if print_uses:
                violations.extend(print_uses)
            else:
                checks_passed += 1

            # Custom / Task-specific conventions
            for rule in self.conventions:
                rule_name = rule.get("name", "custom_rule")
                rule_type = rule.get("type", "ast")
                checks_performed += 1

                if rule_type == "no_sql_formatting":
                    viol = self._check_no_sql_formatting(content, filename)
                    if viol:
                        violations.extend(viol)
                    else:
                        checks_passed += 1
                elif rule_type == "required_subclass":
                    base_cls = rule.get("base_class", "Exception")
                    viol = self._check_subclass_exists(tree, base_cls, filename)
                    if viol:
                        violations.extend(viol)
                    else:
                        checks_passed += 1
                elif rule_type == "regex_forbidden":
                    pattern = rule.get("pattern", "")
                    msg = rule.get("message", f"Forbidden pattern {pattern}")
                    if re.search(pattern, content):
                        violations.append(f"[{filename}] Convention violation: {msg}")
                    else:
                        checks_passed += 1

        score = (checks_passed / checks_performed) if checks_performed > 0 else 1.0
        details = {
            "checks_performed": checks_performed,
            "checks_passed": checks_passed,
            "violation_count": len(violations),
        }
        return round(score, 3), violations, details

    def _check_type_annotations(self, tree: ast.AST, filename: str) -> List[str]:
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_") and node.name != "__init__":
                    continue  # private helpers can be exempt or lower priority
                
                # Check args for annotations (excluding 'self' and 'cls')
                for arg in node.args.args:
                    if arg.arg in ("self", "cls"):
                        continue
                    if arg.annotation is None:
                        violations.append(
                            f"[{filename}:{node.lineno}] Function '{node.name}' parameter '{arg.arg}' lacks type annotation"
                        )
                # Check return annotation (except __init__)
                if node.name != "__init__" and node.returns is None:
                    violations.append(
                        f"[{filename}:{node.lineno}] Function '{node.name}' lacks return type annotation"
                    )
        return violations

    def _check_exception_handling(self, tree: ast.AST, filename: str) -> List[str]:
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    if handler.type is None:
                        violations.append(
                            f"[{filename}:{handler.lineno}] Bare 'except:' clause is forbidden by team conventions"
                        )
                    # Check for swallowed exception: `except ...: pass`
                    if len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass):
                        violations.append(
                            f"[{filename}:{handler.lineno}] Silently swallowed exception ('except ...: pass') is forbidden"
                        )
        return violations

    def _check_docstrings(self, tree: ast.AST, filename: str) -> List[str]:
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("_") and node.name != "__init__":
                    continue
                docstring = ast.get_docstring(node)
                if not docstring or len(docstring.strip()) < 5:
                    violations.append(
                        f"[{filename}:{node.lineno}] Missing docstring for public entity '{node.name}'"
                    )
        return violations

    def _check_no_print(self, tree: ast.AST, filename: str) -> List[str]:
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "print":
                    violations.append(
                        f"[{filename}:{node.lineno}] Use of 'print()' detected; team convention requires 'logging'"
                    )
        return violations

    def _check_no_sql_formatting(self, content: str, filename: str) -> List[str]:
        """Checks for unsafe SQL string formatting (f-strings or .format in query execution)."""
        violations = []
        lines = content.splitlines()
        for idx, line in enumerate(lines, 1):
            if re.search(r"execute\s*\(\s*f[\"'].*SELECT|INSERT|UPDATE|DELETE", line, re.IGNORECASE):
                violations.append(
                    f"[{filename}:{idx}] SQL Injection vulnerability: f-string used in SQL query execution. Must use parameterized queries."
                )
            elif re.search(r"\.format\(.*SELECT|INSERT|UPDATE|DELETE", line, re.IGNORECASE):
                violations.append(
                    f"[{filename}:{idx}] SQL Injection vulnerability: string format used in SQL query. Must use parameterized queries."
                )
        return violations

    def _check_subclass_exists(self, tree: ast.AST, base_class: str, filename: str) -> List[str]:
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == base_class:
                        found = True
                        break
        if not found:
            return [f"[{filename}] Required class inheriting from '{base_class}' not found"]
        return []
