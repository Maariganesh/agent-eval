# AGENTS.md (Candidate Production Standard)

You are an expert software engineer adhering to rigorous engineering team conventions.

## Core Engineering Principles:
1. **Functional Correctness First**: Code must pass all automated test suites and handle edge cases gracefully.
2. **Defensive Validation**: Always validate function arguments and constructor inputs at the boundary. Raise `ValueError` or domain exceptions for invalid parameters.
3. **Type Annotations**: Every function parameter and return type must be explicitly annotated using standard Python typing (`typing.Dict`, `typing.List`, `typing.Tuple`, `typing.Optional`, etc.).
4. **Structured Error Handling**: Define domain exception hierarchies inheriting from a base exception. Never swallow exceptions or use bare `except:`.
5. **Observability**: Use the standard `logging` module. Never use raw `print()` statements in production code.
6. **Security & Parameterization**: All SQL queries must use parameterized placeholders (`?`). String interpolation and format strings in queries are strictly forbidden.
7. **Thread Safety**: Protect shared mutable state with `threading.Lock()` where concurrency is expected.
