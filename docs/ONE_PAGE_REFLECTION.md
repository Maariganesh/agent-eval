# Evaluating Coding Agent Harnesses: Architectural Reflection & Decisions

> **Hard Limit: Exactly One Page (~700 words)**

---

### 1. Concepts Defined & Why

To replace intuition with reproducible evidence, we defined four core concepts:

1. **The Harness Bundle as an Immutable Unit**: A harness is not just `AGENTS.md`; it is the total context delivered to the model: system prompts, active rule files (`rules/*.md`), modular skills (`skills/*/SKILL.md`), tool definitions, and model parameters. Evaluating isolated prompt snippets produces noise; we evaluate the complete assembled bundle.
2. **The Four Cardinal Pillars of Quality**: Code quality is multi-dimensional. We evaluate:
   - *Functional Correctness* (does it run and pass automated unit test suites?);
   - *Convention Compliance* (does it obey architectural invariants, type annotations, and error hierarchies via AST inspection?);
   - *Spec Fulfillment* (does it satisfy business boundary conditions and edge-case rubrics?);
   - *Resource Efficiency* (does the change explode token usage, latency, or dollar cost?).
3. **Regression Guardrails (Asymmetric Trust)**: In engineering teams, trust is lost when a change breaks existing working code. A harness that increases token efficiency or style compliance must *never* be shipped if it breaks previously passing tests. Our verdict engine enforces zero-tolerance functional regression guardrails.
4. **Net Quality Impact Delta ($\Delta$)**: Evaluating absolute scores is misleading across disparate tasks. We measure delta impact ($\text{Candidate} - \text{Baseline}$) across identical benchmark tasks to isolate the causal effect of the harness alteration.

---

### 2. The Five Hardest Decisions

1. **Deterministic Ground-Truth vs. LLM-as-a-Judge**: Relying solely on an LLM to evaluate another LLM introduces judge drift, verbosity bias, and high variance. We decided to ground the primary evaluation in deterministic sandboxed pytest suites and Python AST parsers, reserving LLM judges strictly for semantic requirements.
2. **Hard Guardrail vs. Weighted Trade-off**: Should a +50% gain in convention adherence offset a single failing unit test? We decided **No**. Correctness is non-negotiable. If functional tests regress by $>5\%$, the verdict is forcibly locked to `NEGATIVE`, preventing dangerous rollouts.
3. **First-Class Offline Fixtures vs. Live-Only Runs**: Live API calls are expensive, rate-limited, non-deterministic, and fail without API keys. We decided to build a dual-runner architecture: offline deterministic replay (enabling immediate CI runs and evaluator reproduction with zero keys) alongside live LiteLLM/OpenAI execution.
4. **Scoring Prompt Bloat & Token Inefficiency**: Engineering harnesses easily suffer from "prompt bloat"—stuffing dozens of rules into `AGENTS.md` that yield marginal code gains while inflating input tokens by 400%. We established a cost-penalty threshold where token increases $>60\%$ without commensurate quality improvements trigger a rejection verdict.
5. **AST Structural Inspection vs. Static Linter Subprocesses**: Running external linters (e.g., `ruff`/`flake8`) requires complex environment configuration and lacks custom harness awareness. We built an AST-based analyzer that directly audits Python syntax trees for missing type annotations, bare `except:` clauses, swallowed exceptions, and raw SQL string interpolation.

---

### 3. What Was Cut & Why

- **Free-Form Multi-Turn Agent Swarms**: Cut because non-deterministic agent loops introduce uncontrolled variables (network retries, random tool order). Evaluating harness changes requires strictly controlled single/fixed-turn evaluation to isolate prompt causation.
- **Subjective "Code Cleanliness" Aesthetic Rubrics**: Cut because human opinions on style vary wildly. We replaced subjective scoring with objective AST syntax rules (typed signatures, docstrings, structured logging instead of `print`).
- **Heavyweight Docker Sandbox Daemon**: Cut to guarantee zero-dependency instant execution on Windows, macOS, and Linux, replacing it with an isolated temporary workspace running subprocess pytest execution.

---

### 4. When We Did Not Trust Our Own Tool's Result & What We Did

**The Failure Case**: In our initial run of `task_03_sql_injection` (SQL Query Builder), the candidate harness scored a perfect **100% Functional** and **100% Convention** score, triggering a `POSITIVE` verdict. 

**Why We Did Not Trust It**: Manual inspection of the generated code revealed that while the agent implemented the `select()` and `where()` builder methods, it allowed field names containing malicious SQL injection strings (`"id; DROP TABLE users; --"`). The initial test suite only exercised happy-path identifiers like `"username"` and `"status"`, and the convention checker only searched for raw `SELECT` query execution rather than identifier sanitization in builder classes. The tool reported a false sense of security.

**The Action Taken**: We instituted a two-part fix:
1. **Adversarial Test Injection**: We augmented the benchmark test suite with malicious identifier payloads to explicitly test boundary rejection.
2. **AST & Regex Identifier Validation**: We upgraded the convention evaluator to enforce strict whitelist regex checks (`^[a-zA-Z0-9_]+$`) on all SQL identifiers. Upon re-running, the insecure candidate failed until the harness was explicitly equipped with security rules—restoring mathematical trust to the evaluation.
