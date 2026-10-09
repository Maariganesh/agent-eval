"""
Functional correctness evaluator: executes unit tests in an isolated sandbox.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Tuple


def evaluate_functional(
    code_files: Dict[str, str],
    test_files: Dict[str, str],
    test_command: str = "pytest",
    timeout: int = 15,
) -> Tuple[float, int, int, str]:
    """
    Executes tests against generated code in an isolated temporary directory.
    Returns:
        (functional_score [0.0..1.0], tests_passed, tests_total, test_output)
    """
    with tempfile.TemporaryDirectory(prefix="agent_eval_test_") as tmpdir:
        tmppath = Path(tmpdir)
        
        # Write generated code files
        for rel_path, content in code_files.items():
            dest = tmppath / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            
        # Write test files
        for rel_path, content in test_files.items():
            dest = tmppath / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

        # Run pytest inside the isolated environment
        # Use python -m pytest to avoid path resolution issues on Windows
        cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short"]
        
        env = os.environ.copy()
        # Add the tempdir to PYTHONPATH so test imports find the generated module
        pythonpath = str(tmppath)
        if "PYTHONPATH" in env:
            pythonpath = f"{pythonpath}{os.pathsep}{env['PYTHONPATH']}"
        env["PYTHONPATH"] = pythonpath

        try:
            res = subprocess.run(
                cmd,
                cwd=str(tmppath),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
            
            # Parse pytest summary line (e.g. "3 passed, 1 failed in 0.12s" or "4 passed in 0.05s")
            passed, total = _parse_pytest_output(output)
            
            score = (passed / total) if total > 0 else 0.0
            return score, passed, total, output.strip()

        except subprocess.TimeoutExpired:
            return 0.0, 0, 1, f"Execution timed out after {timeout} seconds (possible infinite loop)."
        except Exception as e:
            return 0.0, 0, 1, f"Execution error: {str(e)}"


def _parse_pytest_output(output: str) -> Tuple[int, int]:
    """
    Extracts passed and total test counts from pytest stdout.
    """
    passed = 0
    failed = 0
    errors = 0
    
    for line in output.splitlines():
        line_clean = line.strip().lower()
        if "passed" in line_clean or "failed" in line_clean or "error" in line_clean:
            # Look for summary lines like: "=== 2 passed, 1 failed in 0.05s ==="
            # or "=== 3 passed in 0.02s ==="
            parts = line_clean.replace("=", "").replace(",", " ").split()
            for i, part in enumerate(parts):
                if part.isdigit() and i + 1 < len(parts):
                    label = parts[i + 1]
                    if "passed" in label:
                        passed = int(part)
                    elif "failed" in label:
                        failed = int(part)
                    elif "error" in label:
                        errors = int(part)

    total = passed + failed + errors
    if total == 0:
        # Fallback if no explicit summary matched but tests ran
        if "collected" in output and "passed" in output and failed == 0:
            import re
            m = re.search(r"collected (\d+) item", output)
            if m:
                total = int(m.group(1))
                passed = total
    return passed, total
