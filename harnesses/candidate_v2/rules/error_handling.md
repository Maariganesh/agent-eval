# Rule: Error Handling Standards

1. Never use bare `except:` clauses. Always catch specific exception classes.
2. Never swallow exceptions with `except ...: pass`.
3. Distinguish between retryable/transient errors and permanent/fatal errors in distributed workflows.
4. Define clean domain exception classes inheriting from an explicit base `Exception`.
