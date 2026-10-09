# Rule: SQL Query Security & Injection Prevention

1. Under no circumstances should user variables or inputs be concatenated or formatted into raw SQL strings.
2. Query builders must output parameterized SQL queries with `?` or `%s` parameter placeholders.
3. Validate identifiers (table names, column names) against a strict whitelist or regex `^[a-zA-Z0-9_]+$`.
