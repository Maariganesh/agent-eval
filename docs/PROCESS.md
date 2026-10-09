# Development Process & Human-in-the-Loop Audit Log

This document details the complete process followed to construct the `agent-eval` tool, including the prompting strategy, manual verification steps, mistakes made during agent generation, and how they were caught and corrected.

---

## 1. What We Asked (Prompting Sequence)

The development was structured into targeted prompts adhering to test-driven and modular development:

1. **System & Domain Architecture Prompt**:
   - *Prompt*: "Design the core domain models for an agent harness evaluation tool. The tool must evaluate baseline vs candidate harnesses across four dimensions: functional correctness (test suites), team conventions (typing, error handling, AST rules), business spec fulfillment (rubrics), and token cost economics. Define Pydantic models in `harness_eval/models.py`."
2. **Evaluator Metrics & Sandboxing Prompt**:
   - *Prompt*: "Implement the dimensional evaluators. For functional correctness, execute `pytest` in an isolated temporary sandbox with path isolation. For conventions, use Python AST analysis to detect missing type hints, bare `except:` clauses, and raw SQL string interpolation. For cost, calculate prompt and completion tokens with model pricing."
3. **Verdict & Guardrail Decision Engine Prompt**:
   - *Prompt*: "Build the verdict engine in `harness_eval/verdict.py`. Define regression guardrails: if any passing test regresses, the change MUST be marked `NEGATIVE`. Also penalize prompt bloat if tokens increase >60% without quality gain."
4. **CLI, Runners, & Benchmark Task Suite Prompt**:
   - *Prompt*: "Create `harness_eval/cli.py` with an `evaluate` command, both offline deterministic fixture replaying and live LLM runner support, and generate 4 realistic benchmark engineering tasks."

---

## 2. What We Checked by Hand (Manual Audits)

At each stage, human-in-the-loop verification was conducted rather than trusting agent outputs blindly:

1. **Sandbox Isolation Audit**:
   - *Check*: Inspected `harness_eval/metrics/functional.py` to ensure temporary directories are cleaned up and `sys.executable -m pytest` does not mutate the current workspace or overwrite benchmark fixtures.
   - *Result*: Verified that `tempfile.TemporaryDirectory` writes generated code and tests into a disposable sandbox with customized `PYTHONPATH`.
2. **AST Convention Precision Audit**:
   - *Check*: Tested AST visitor logic against edge cases like `def __init__(self)` (which should not be penalized for lacking a return type annotation) and private helpers `_helper()` (which can have looser typing).
   - *Result*: Added explicit filters so `__init__`, `self`, and `cls` parameters are correctly exempted.
3. **Adversarial SQL Injection Attack Verification**:
   - *Check*: Inspected `task_03_sql_injection` to verify if malicious identifier attacks (`users; DROP TABLE users; --`) were caught.
   - *Result*: Identified that initial regex was too lenient; manually tightened it to enforce strict identifier whitelisting (`^[a-zA-Z0-9_]+$`).
4. **CI/CD Regression Exit Code Verification**:
   - *Check*: Ran `python evaluate.py evaluate --candidate harnesses/candidate_regressive --fail-on-regression` directly in the shell to ensure non-zero exit code (`exit code 2`) is returned when regressions are detected.
   - *Result*: Confirmed automated pipeline failure stops broken harnesses from deploying.

---

## 3. Where the Agent Was Wrong & How We Fixed It

During the iterative build, the agent encountered four concrete bugs and failure modes:

### Issue 1: Missing Variable Assignment (`harness_key`)
- **What happened**: When modifying `OfflineFixtureRunner.run_task` to support multiple directory resolution patterns, the agent deleted the line defining `harness_key = harness.name.lower().replace(" ", "_")` before using it in `candidate_dirs`.
- **How it was caught**: Running `python evaluate.py` triggered `NameError: name 'harness_key' is not defined`.
- **Fix**: Re-instated the variable definition at the start of `run_task`.

### Issue 2: Windows CP1252 Terminal Crash (`UnicodeEncodeError: '\u0394'`)
- **What happened**: The agent used the Greek delta character `Δ` in Rich table column headers (`"Func Δ"`, `"Conv Δ"`), and Unicode bullet characters (`•`, `➜`) in console text. On Windows PowerShell / CMD environments where standard output defaults to legacy `cp1252`, Python threw:
  ```
  UnicodeEncodeError: 'charmap' codec can't encode character '\u0394' in position 5
  ```
- **How it was caught**: The CLI crashed on table rendering during the first end-to-end evaluation run.
- **Fix**: Replaced all Greek delta symbols with ASCII `"Func Delta"`, `"Conv Delta"`, and replaced bullets with `*` and arrows with `->`. This made terminal reporting 100% portable across Windows, macOS, and Linux.

### Issue 3: Click Subcommand Dispatch with Group-Level Options
- **What happened**: When executing `python evaluate.py --baseline ...`, Click threw `Error: No such option '--baseline'` because Click CLI groups expect either `evaluate` subcommand explicitly or group-level argument dispatch.
- **How it was caught**: Testing CLI invocations with flags without specifying the word `evaluate`.
- **Fix**: Added intelligent argument dispatch in `evaluate.py` and `harness_eval/cli.py` that automatically detects when options are passed directly and routes them to the `evaluate` command.

### Issue 4: Blind Trust in False-Positive Benchmark Score (Task 3)
- **What happened**: The candidate query builder achieved 100% pass rate in initial tests, but human inspection found it vulnerable to SQL injection in table and field names. The test suite was too forgiving.
- **How it was caught**: Manual code review of the generated fixture.
- **Fix**: Augmented the test suite with adversarial SQL injection test cases and added AST rule enforcement for identifier regex validation.

---

## 4. Session Transcript & Verification Evidence

The full session transcript is stored in the agent IDE log directory:
- **Conversation ID**: `ecc7b4a6-9b82-4ab6-802c-3d3be9d3b962`
- **Transcript Logs**: `C:\Users\mitra\.gemini\antigravity-ide\brain\ecc7b4a6-9b82-4ab6-802c-3d3be9d3b962\.system_generated\logs\transcript.jsonl`
- **Task Execution Log**: `C:\Users\mitra\.gemini\antigravity-ide\brain\ecc7b4a6-9b82-4ab6-802c-3d3be9d3b962\.system_generated\tasks\task-171.log`

### Test Verification
All 14 unit tests pass cleanly:
```bash
python -m pytest -v tests/
# 14 passed in 0.80s
```
