# AGENTS.md — Development Harness for Agent-Eval Framework

This file defines the engineering protocols, quality standards, and evaluation criteria used during the development of the `agent-eval` tool.

## Architectural Mandates
1. **Zero-Setup Quickstart**: The evaluation tool must run out of the box with zero required API keys using deterministic offline fixtures, while maintaining full support for live LLMs via LiteLLM/OpenAI.
2. **Deterministic Evidence Over Opinion**: Never evaluate code quality with subjective vibes. Code quality must be anchored in:
   - Automated isolated test execution (pytest).
   - AST (Abstract Syntax Tree) inspection for structural conventions, typing, error handling, and security.
   - Specific rubric assertions for edge cases.
   - Accurate token counting and model pricing tables.
3. **Cross-Platform Resiliency**: All terminal output, file path resolution, and child processes must be completely resilient across Windows (PowerShell/cmd), Linux (bash), and macOS (zsh). Avoid raw Unicode Greek glyphs (e.g., `\u0394`) or unsupported terminal encodings that fail on legacy Windows cp1252 consoles.
4. **Asymmetric Trust & Regression Guardrails**: A harness change that breaks working unit tests on any task must trigger an immediate `NEGATIVE` verdict regardless of token savings or style scores.

## Development Workflow
- When writing modules, define strict Pydantic domain models in `models.py`.
- Keep evaluation metrics modular (`harness_eval/metrics/functional.py`, `convention.py`, `fulfillment.py`, `cost.py`).
- Implement the CLI using `click` with comprehensive flags (`--baseline`, `--candidate`, `--tasks`, `--report-html`, `--report-md`, `--fail-on-regression`).
- Verify every change with automated `pytest` test suites.
