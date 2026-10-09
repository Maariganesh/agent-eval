"""
Secure parameterized SQL Query Builder preventing SQL injection and identifier attacks.
"""
from __future__ import annotations

import re
from typing import Any, List, Sequence, Tuple

_IDENTIFIER_REGEX = re.compile(r"^[a-zA-Z0-9_]+$")
_ALLOWED_OPERATORS = {"=", "!=", ">", "<", ">=", "<=", "LIKE", "IN"}


class QueryBuilder:
    """
    Secure fluent query builder generating parameterized SQL statements.
    """

    def __init__(self, table: str) -> None:
        """
        Initializes the query builder for a target table.
        """
        if not table or not _IDENTIFIER_REGEX.match(table):
            raise ValueError(f"Invalid table identifier: {table!r}")
        self._table: str = table
        self._columns: List[str] = ["*"]
        self._where_clauses: List[str] = []
        self._params: List[Any] = []

    def select(self, *columns: str) -> QueryBuilder:
        """
        Specifies projection columns for the query.
        """
        if columns:
            valid_cols = []
            for col in columns:
                if col != "*" and not _IDENTIFIER_REGEX.match(col):
                    raise ValueError(f"Invalid column identifier: {col!r}")
                valid_cols.append(col)
            self._columns = valid_cols
        return self

    def where(self, field: str, op: str, value: Any) -> QueryBuilder:
        """
        Adds a parameterized WHERE clause.
        """
        if not field or not _IDENTIFIER_REGEX.match(field):
            raise ValueError(f"Invalid field identifier: {field!r}")
        
        op_clean = op.strip().upper()
        if op_clean not in _ALLOWED_OPERATORS:
            raise ValueError(f"Disallowed or invalid SQL operator: {op!r}")

        self._where_clauses.append(f"{field} {op_clean} ?")
        self._params.append(value)
        return self

    def build(self) -> Tuple[str, Tuple[Any, ...]]:
        """
        Builds and returns the parameterized SQL string and the tuple of parameter values.
        """
        cols_str = ", ".join(self._columns)
        if self._where_clauses:
            where_str = " AND ".join(self._where_clauses)
            sql = f"SELECT {cols_str} FROM {self._table} WHERE {where_str}"
        else:
            sql = f"SELECT {cols_str} FROM {self._table}"

        return sql, tuple(self._params)
