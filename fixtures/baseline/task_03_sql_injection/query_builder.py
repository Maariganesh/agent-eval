class QueryBuilder:
    def __init__(self, table):
        self.table = table
        self.columns = ["*"]
        self.clauses = []

    def select(self, *columns):
        if columns:
            self.columns = list(columns)
        return self

    def where(self, field, op, value):
        # Insecure direct formatting - vulnerable to SQL injection
        self.clauses.append(f"{field} {op} '{value}'")
        return self

    def build(self):
        col_str = ", ".join(self.columns)
        where_str = " AND ".join(self.clauses)
        if where_str:
            sql = f"SELECT {col_str} FROM {self.table} WHERE {where_str}"
        else:
            sql = f"SELECT {col_str} FROM {self.table}"
        return sql, ()
