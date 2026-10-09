"""
Idempotent payment retry workflow with structured error handling and logging.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    """Base domain exception for all payment-related failures."""
    pass


class TransientPaymentError(PaymentError):
    """Recoverable payment error (e.g., network timeout, service 503) suitable for retry."""
    pass


class FatalPaymentError(PaymentError):
    """Non-recoverable payment error (e.g., card declined, validation failure)."""
    pass


def execute_payment_with_retry(
    client_fn: Callable[[str], Dict[str, Any]],
    idempotency_key: str,
    max_retries: int = 3,
    backoff_factor: float = 0.05,
) -> Dict[str, Any]:
    """
    Executes a payment transaction with exponential backoff on transient errors.
    """
    if max_retries <= 0:
        raise ValueError(f"max_retries must be >= 1, got {max_retries}")

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Dispatching payment attempt %d for key %s", attempt, idempotency_key)
            return client_fn(idempotency_key)
        except FatalPaymentError as fatal_err:
            logger.error("Fatal unrecoverable payment error for key %s: %s", idempotency_key, fatal_err)
            raise fatal_err
        except TransientPaymentError as trans_err:
            last_error = trans_err
            logger.warning("Transient error on attempt %d for key %s: %s", attempt, idempotency_key, trans_err)
            if attempt < max_retries:
                sleep_duration = backoff_factor * (2 ** (attempt - 1))
                time.sleep(sleep_duration)
            else:
                break
        except Exception as generic_err:
            logger.error("Unexpected exception during payment: %s", generic_err)
            raise PaymentError(f"Unexpected payment failure: {generic_err}") from generic_err

    raise PaymentError(f"Payment exhausted all {max_retries} retry attempts: {last_error}")
