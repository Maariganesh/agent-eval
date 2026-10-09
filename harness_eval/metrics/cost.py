"""
Cost and token usage calculator for agent harnesses.
Tracks prompt tokens, completion tokens, dollar costs, and efficiency metrics.
"""
from __future__ import annotations

from typing import Dict, Tuple

# Pricing per million tokens (USD)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-7-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "default": {"input": 2.50, "output": 10.00},
}


def count_tokens(text: str) -> int:
    """
    Estimates token count accurately using tiktoken if available, or 4 chars/token heuristic.
    """
    if not text:
        return 0
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # Fallback estimation: average 1 token ~= 4 chars or 0.75 words
        return max(1, len(text) // 4)


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "gpt-4o",
) -> Tuple[float, int]:
    """
    Computes estimated cost in USD and total tokens.
    Returns:
        (estimated_cost_usd, total_tokens)
    """
    rates = MODEL_PRICING.get(model.lower(), MODEL_PRICING["default"])
    input_cost = (input_tokens / 1_000_000) * rates["input"]
    output_cost = (output_tokens / 1_000_000) * rates["output"]
    total_cost = round(input_cost + output_cost, 6)
    total_tokens = input_tokens + output_tokens
    return total_cost, total_tokens
