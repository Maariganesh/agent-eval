class CursorPagination:
    def encode_cursor(self, item_id, timestamp):
        # Naive colon string representation without base64 encoding
        return f"{item_id}:{timestamp}"

    def decode_cursor(self, cursor):
        try:
            parts = cursor.split(":")
            return parts[0], float(parts[1])
        except Exception:
            raise ValueError("Invalid cursor")

    def paginate(self, items, limit, cursor=None):
        # Missing limit range validation (allows limit <= 0 or > 100)
        start_idx = 0
        if cursor:
            item_id, ts = self.decode_cursor(cursor)
            for i, itm in enumerate(items):
                if itm["id"] == item_id:
                    start_idx = i + 1
                    break

        page_items = items[start_idx : start_idx + limit]
        has_next = (start_idx + limit) < len(items)
        next_c = self.encode_cursor(page_items[-1]["id"], page_items[-1]["timestamp"]) if (has_next and page_items) else None

        return {
            "items": page_items,
            "has_next_page": has_next,
            "next_cursor": next_c,
            "total_count": len(items),
        }
