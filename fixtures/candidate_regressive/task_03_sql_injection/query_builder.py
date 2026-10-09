# Regressive query builder with vulnerable string concatenation
class QueryBuilder:
    def __init__(self, table):
        self.table = table
        self.where_str = ""

    def select(self, *columns):
        return self

    def where(self, field, op, value):
        self.where_str = f"{field} {op} '{value}'"
        return self

    def build(self):
        sql = f"SELECT * FROM {self.table} WHERE {self.where_str}"
        return sql, ()
