---
name: harness-evaluation
description: Specialized skill for benchmark-driven evaluation of agent harnesses, prompts, and skills.
---

# Harness Evaluation Skill

## Purpose
Enables automated comparative evaluation of coding agent harnesses (baseline vs candidate) across multidimensional criteria: functional correctness, team conventions, business requirements, and token economics.

## Evaluation Protocol
1. **Benchmark Selection**: Select realistic tasks with isolated unit tests and unambiguous rubrics.
2. **Context Assembly**: Assemble the candidate harness (AGENTS.md + rules + skills + tools + prompt) and run in an isolated workspace.
3. **Multi-Pillar Verification**:
   - `Functional`: Execute tests via `pytest -v --tb=short` in an isolated temp directory.
   - `Conventions`: Parse AST to verify typing, exception handling, docstrings, and security patterns.
   - `Rubric`: Check domain invariants and edge-case handling.
   - `Cost`: Track input/output tokens and calculate USD cost based on model rates.
4. **Verdict Calculation**:
   - Compute deltas: $\Delta \text{Functional}$, $\Delta \text{Convention}$, $\Delta \text{Fulfillment}$, $\Delta \text{Tokens}$.
   - Apply regression guardrails: Reject if functional tests regress or if cost increases by >60% without quality gain.
