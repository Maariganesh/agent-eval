# Regressive pagination implementation
class CursorPagination:
    def encode_cursor(self, item_id, timestamp):
        return f"{item_id}-{timestamp}"

    def decode_cursor(self, cursor):
        try:
            p = cursor.split("-")
            return p[0], float(p[1])
        except:
            return "none", 0.0

    def paginate(self, items, limit, cursor=None):
        return {"items": items, "has_next_page": False, "next_cursor": None, "total_count": len(items)}
