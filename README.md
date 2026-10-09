# agent-eval: Harness Evaluation Tool for Coding Agents

[![Tests](https://img.shields.io/badge/pytest-14%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)]()

> **Evidence-based trust for your coding agent harness.**  
> Know definitively whether a change to `AGENTS.md`, rules, skills, MCPs, or models improves code quality before rolling it out to your engineering team.

---

## The Problem

Engineering teams continually iterate on their coding agent harnesses: updating `AGENTS.md`, writing custom skills, adding rules, testing new MCP tools, or switching models (e.g., Sonnet 3.5 to 3.7). Every change is made with good intentions, but **almost nobody evaluates whether the change actually improves code quality**.

Quality is multifaceted:
- **The code works**: It runs and passes automated unit tests.
- **It follows team conventions**: It adheres to type safety, error hierarchies, and security invariants.
- **It fulfills business specifications**: It handles edge cases and boundary conditions.
- **It is cost-efficient**: It does not burn through token budgets with bloated instructions.

`agent-eval` replaces gut feelings and anecdotal impressions with a rigorous, reproducible evaluation pipeline that produces evidence-based verdicts: **POSITIVE (Safe to Ship)**, **NEGATIVE (Reject)**, or **INCONCLUSIVE (Needs More Data)**.

---

## Key Architecture & Evaluation Pillars

```
                     ┌──────────────────────────────────────────────┐
                     │          EVALUATION ORCHESTRATOR             │
                     └──────────────────────┬───────────────────────┘
                                            │
                     ┌──────────────────────┴───────────────────────┐
                     │                                              │
              [Baseline Harness]                           [Candidate Harness]
              • AGENTS.md (control)                        • AGENTS.md (treatment)
              • Rules & Skills                             • Rules, Skills & Tools
                     │                                              │
                     └──────────────────────┬───────────────────────┘
                                            │
                            ┌───────────────▼───────────────┐
                            │    BENCHMARK TASK SUITE       │
                            │  • Rate Limiter               │
                            │  • Payment Retry              │
                            │  • SQL Query Sanitizer        │
                            │  • API Cursor Pagination      │
                            └───────────────┬───────────────┘
                                            │
                     ┌──────────────────────┴───────────────────────┐
                     │          FOUR DIMENSIONAL EVALUATORS         │
                     │  1. Functional Correctness (pytest sandbox)  │
                     │  2. Convention Compliance (AST inspection)   │
                     │  3. Business Spec Rubrics (Invariants)       │
                     │  4. Token Cost & Economics (Pricing model)   │
                     └──────────────────────┬───────────────────────┘
                                            │
                     ┌──────────────────────▼───────────────────────┐
                     │      VERDICT & REGRESSION GUARDRAILS         │
                     │  • Asymmetric Correctness Protection         │
                     │  • Net Quality Impact Score (Δ)              │
                     │  • Prompt Bloat Penalty (>60% token jump)    │
                     └──────────────────────┬───────────────────────┘
                                            │
                     ┌──────────────────────▼───────────────────────┐
                     │             MULTI-FORMAT REPORTING           │
                     │  • Rich Terminal Visualizer                  │
                     │  • Interactive Dark-Mode HTML Dashboard      │
                     │  • GitHub PR Markdown Export                 │
                     │  • CI/CD Non-Zero Exit Code Gating           │
                     └──────────────────────────────────────────────┘
```

---

## Quickstart (Zero Setup, No API Key Required!)

The repository includes pre-recorded, realistic offline fixtures that execute deterministically in seconds:

```bash
# 1. Run the default evaluation pipeline (Baseline vs Candidate v2)
python evaluate.py
```

Or run the full comparative demo highlighting both positive and negative scenarios:

```bash
python run_demo.py
```

### Installation

```bash
# Optional editable installation
pip install -e .
```

Once installed, you can use the CLI directly:
```bash
agent-eval evaluate
```

---

## Real Example Walkthrough

### Scenario 1: Positive Harness Change (Candidate v2)
We compare `harnesses/baseline` against `harnesses/candidate_v2`:
- **Changes in Candidate v2**: Added structured `AGENTS.md`, strict typing rules, domain exception hierarchy requirements, SQL injection security rules, and defensive coding skills.

Run the evaluation:
```bash
python evaluate.py evaluate --baseline harnesses/baseline --candidate harnesses/candidate_v2
```

**Results:**
- **Verdict**: `POSITIVE`
- **Functional Correctness**: **+42.5%** test pass rate improvement (51.2% -> 93.8%).
- **Convention Adherence**: **+37.5%** compliance (zero bare `except:`, complete type annotations).
- **Business Spec Fulfillment**: **+41.7%** (sliding window expiration, idempotency key verification, parameterization).
- **Net Quality Impact Score**: **+41.0 pts**
- **Token Variance**: +42.1% (efficiently justified by the quality leap).
- **Output Artifacts**: [eval_report_positive.html](eval_report_positive.html) | [eval_report_positive.md](eval_report_positive.md)

---

### Scenario 2: Detecting a Regressive Change (Candidate Regressive)
We evaluate `harnesses/candidate_regressive`, which introduced 500 lines of prompt bloat, confusing exception rules, and bad SQL formatting patterns:

```bash
python evaluate.py evaluate --baseline harnesses/baseline --candidate harnesses/candidate_regressive
```

**Results:**
- **Verdict**: `NEGATIVE`
- **Guardrail Triggered**: Critical functional regression on 3 tasks (Rate Limiter -50%, Payment Retry -50%, Pagination -40%).
- **Token Overhead**: **+372.3%** token explosion (18,130 wasted tokens) with net quality drop (-27.4 pts).
- **Recommendation**: *Do NOT roll out this harness change to engineering teams.*
- **Output Artifacts**: [eval_report_negative.html](eval_report_negative.html) | [eval_report_negative.md](eval_report_negative.md)

---

## CLI Command Reference

The `evaluate` command provides complete configuration flexibility:

```text
Usage: python evaluate.py evaluate [OPTIONS]

Options:
  -b, --baseline PATH       Directory containing baseline harness (AGENTS.md, rules, skills). [default: harnesses/baseline]
  -c, --candidate PATH      Directory containing candidate harness to evaluate. [default: harnesses/candidate_v2]
  -t, --tasks PATH          Path to tasks.yaml benchmark file or benchmark folder. [default: benchmarks/tasks.yaml]
  --fixtures PATH           Path to offline evaluation fixtures. [default: fixtures]
  --live                    Execute live LLM calls instead of deterministic offline fixtures.
  --model TEXT              Model identifier if running in --live mode. [default: gpt-4o]
  --report-html PATH        Output file path for interactive HTML dashboard. [default: eval_report.html]
  --report-md PATH          Output file path for Markdown report. [default: eval_report.md]
  --report-json PATH        Output file path for machine-readable JSON data. [default: eval_report.json]
  --fail-on-regression      Exit with non-zero status if evaluation verdict is NEGATIVE (for CI/CD).
  --help                    Show this message and exit.
```

---

## Live LLM Execution

To run evaluation against a live model (e.g. OpenAI GPT-4o, Claude 3.5 Sonnet):

```bash
export OPENAI_API_KEY="your-api-key"
python evaluate.py evaluate --live --model gpt-4o
```

---

## CI/CD Automated Quality Gate

Prevent broken agent rules from merging to `main` by adding `agent-eval` to your CI pipeline:

```yaml
# .github/workflows/agent-eval.yml
name: Agent Harness Quality Gate
on:
  pull_request:
    paths:
      - 'AGENTS.md'
      - 'rules/**'
      - 'skills/**'

jobs:
  evaluate-harness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e .
      - name: Run Harness Evaluation
        run: |
          agent-eval evaluate \
            --baseline ./production-harness \
            --candidate ./pr-harness \
            --fail-on-regression
```

If the pull request regresses test pass rates or bloats token cost without quality gains, the step fails with exit code `2`, blocking merge.

---

## Project Structure

```
├── README.md                      # Complete system documentation (Deliverable 1)
├── AGENTS.md                      # Harness instructions used to build the tool (Deliverable 5)
├── docs/                          # Core assignment documentation
│   ├── ONE_PAGE_REFLECTION.md     # Deliverable 4: Hard limit 1-page design & reflection
│   └── PROCESS.md                 # Deliverable 5: Process transcript, audit log, error resolutions
├── reports/                       # Generated evaluation reports
│   ├── eval_report_positive.html  # Interactive HTML Dashboard (Positive case)
│   ├── eval_report_negative.html  # Interactive HTML Dashboard (Negative case)
│   ├── eval_report_positive.md    # Markdown Summary (Positive case)
│   └── eval_report_negative.md    # Markdown Summary (Negative case)
├── .agents/skills/
│   └── harness-evaluation/        # Skill definition for agent evaluation
│       └── SKILL.md
├── evaluate.py                    # Root convenience launcher
├── run_demo.py                    # Multi-scenario demo script
├── pyproject.toml                 # Package configuration
├── harness_eval/                  # Core Python Package
│   ├── cli.py                     # Click CLI entrypoint with `evaluate` command
│   ├── engine.py                  # Evaluation orchestrator
│   ├── models.py                  # Domain models (Harness, Task, Metrics, Verdict)
│   ├── runner.py                  # Runners (OfflineFixtureRunner, LiveLLMRunner)
│   ├── verdict.py                 # Decision engine & regression guardrails
│   ├── metrics/
│   │   ├── functional.py          # Isolated pytest sandbox execution
│   │   ├── convention.py          # AST typing, error handling, and security auditing
│   │   ├── fulfillment.py         # Business spec rubric engine
│   │   └── cost.py                # Token counter & model cost calculation
│   └── reporting/
│       ├── console.py             # Rich terminal report renderer
│       ├── html.py                # Interactive dark-mode HTML dashboard generator
│       └── markdown.py            # GitHub PR Markdown export generator
├── harnesses/                     # Real harnesses for evaluation
│   ├── baseline/                  # Control harness (minimal prompt)
│   ├── candidate_v2/              # Improved harness (rules, typing, skills)
│   └── candidate_regressive/      # Regressive harness (prompt bloat, anti-patterns)
├── benchmarks/                    # Benchmark tasks
│   └── tasks.yaml                 # Task specifications, starter files, tests, rubrics
├── fixtures/                      # Pre-recorded realistic agent outputs
│   ├── baseline/
│   ├── candidate_v2/
│   └── candidate_regressive/
└── tests/                         # Unit test suite for the evaluation tool
    ├── test_engine.py
    ├── test_verdict.py
    ├── test_metrics.py
    └── test_cli.py
```

---

## Assessment Deliverables Cross-Reference

| Deliverable | Description | File Location |
| :--- | :--- | :--- |
| **1. Repository & README** | Runnable tool with real example walkthrough | [README.md](README.md) |
| **2. Evidenced Report** | Multi-dimensional positive/negative impact evidence | [reports/eval_report_positive.html](reports/eval_report_positive.html) & [reports/eval_report_negative.html](reports/eval_report_negative.html) |
| **3. `evaluate` Command** | Command line tool with reporting & CI gates | `python evaluate.py evaluate` / `agent-eval` |
| **4. One-Page Document** | Hard limit 1 page: concepts, 5 hardest decisions, cuts, trust failure case | [docs/ONE_PAGE_REFLECTION.md](docs/ONE_PAGE_REFLECTION.md) |
| **5. Process & Transcript** | Prompts, manual audit checkpoints, bugs caught & session transcript | [docs/PROCESS.md](docs/PROCESS.md), [AGENTS.md](AGENTS.md), and [.agents/skills/](.agents/skills/harness-evaluation/SKILL.md) |
