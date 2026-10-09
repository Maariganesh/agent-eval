#!/usr/bin/env python
"""
Root convenience entrypoint for running the harness evaluation tool.
Usage:
    python evaluate.py
    python evaluate.py --baseline harnesses/baseline --candidate harnesses/candidate_v2
    python evaluate.py --baseline harnesses/baseline --candidate harnesses/candidate_regressive
"""
import sys
from harness_eval.cli import main

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] not in ["evaluate", "--help", "-h"]:
        sys.argv.insert(1, "evaluate")
    elif len(sys.argv) == 1:
        sys.argv.append("evaluate")
    main()
