#!/usr/bin/env python
"""
Interactive demonstration script for the Agent Harness Evaluation framework.
Runs both:
  1. A POSITIVE evaluation scenario (Baseline vs Candidate v2)
  2. A NEGATIVE evaluation scenario (Baseline vs Candidate Regressive)
"""
import subprocess
import sys


def main():
    print("=" * 80)
    print("RUNNING DEMO 1: POSITIVE EVALUATION (Baseline vs Candidate v2)")
    print("Scenario: Enhanced harness with strict typing, domain errors & security rules")
    print("=" * 80)
    subprocess.run([
        sys.executable, "evaluate.py", "evaluate",
        "--baseline", "harnesses/baseline",
        "--candidate", "harnesses/candidate_v2",
        "--report-html", "eval_report_positive.html",
        "--report-md", "eval_report_positive.md",
        "--report-json", "eval_report_positive.json",
    ])

    print("\n" + "=" * 80)
    print("RUNNING DEMO 2: NEGATIVE EVALUATION (Baseline vs Candidate Regressive)")
    print("Scenario: Bloated harness with prompt anti-patterns causing test regressions")
    print("=" * 80)
    subprocess.run([
        sys.executable, "evaluate.py", "evaluate",
        "--baseline", "harnesses/baseline",
        "--candidate", "harnesses/candidate_regressive",
        "--report-html", "eval_report_negative.html",
        "--report-md", "eval_report_negative.md",
        "--report-json", "eval_report_negative.json",
    ])

    print("\n" + "=" * 80)
    print("DEMO COMPLETE!")
    print("Generated Reports:")
    print("  - eval_report_positive.html (Interactive HTML Dashboard)")
    print("  - eval_report_negative.html (Interactive HTML Dashboard)")
    print("  - eval_report_positive.md   (Markdown Summary)")
    print("  - eval_report_negative.md   (Markdown Summary)")
    print("=" * 80)


if __name__ == "__main__":
    main()
