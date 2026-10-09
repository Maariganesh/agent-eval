"""
Cursor-based pagination engine with URL-safe base64 encoding and bounds validation.
"""
from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Optional, Tuple


class CursorPagination:
    """
    Handles robust cursor-based pagination for high-volume datasets.
    """

    def encode_cursor(self, item_id: str, timestamp: float) -> str:
        """
        Encodes item id and timestamp into a secure URL-safe base64 cursor token.
        """
        payload = json.dumps({"id": str(item_id), "ts": float(timestamp)})
        return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")

    def decode_cursor(self, cursor: str) -> Tuple[str, float]:
        """
        Decodes a URL-safe base64 cursor back to item ID and timestamp.
        """
        if not cursor or not isinstance(cursor, str):
            raise ValueError("Cursor must be a non-empty string")
        try:
            raw_bytes = base64.urlsafe_b64decode(cursor.encode("ascii"))
            data = json.loads(raw_bytes.decode("utf-8"))
            return str(data["id"]), float(data["ts"])
        except Exception as e:
            raise ValueError(f"Malformed or invalid cursor payload: {e}") from e

    def paginate(
        self,
        items: List[Dict[str, Any]],
        limit: int,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Paginates an ordered sequence of dictionary items by cursor token.
        """
        if limit <= 0 or limit > 100:
            raise ValueError(f"Pagination limit must be between 1 and 100, got {limit}")

        start_index = 0
        if cursor:
            target_id, _ = self.decode_cursor(cursor)
            found = False
            for idx, item in enumerate(items):
                if item.get("id") == target_id:
                    start_index = idx + 1
                    found = True
                    break
            if not found:
                # If cursor id not found, start after end or beginning
                start_index = 0

        page_items = items[start_index : start_index + limit]
        has_next = (start_index + limit) < len(items)

        next_cursor: Optional[str] = None
        if has_next and page_items:
            last_item = page_items[-1]
            next_cursor = self.encode_cursor(str(last_item["id"]), float(last_item["timestamp"]))

        return {
            "items": page_items,
            "has_next_page": has_next,
            "next_cursor": next_cursor,
            "total_count": len(items),
        }
