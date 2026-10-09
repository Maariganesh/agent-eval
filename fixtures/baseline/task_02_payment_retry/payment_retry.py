import time

class PaymentError(Exception):
    pass

class TransientPaymentError(PaymentError):
    pass

class FatalPaymentError(PaymentError):
    pass

def execute_payment_with_retry(client_fn, idempotency_key, max_retries=3, backoff_factor=0.05):
    # Baseline naive retry: catches all exceptions without respecting fatal error hierarchy
    attempt = 0
    while attempt < max_retries:
        try:
            print(f"Attempting payment for {idempotency_key}...")
            return client_fn(idempotency_key)
        except Exception as e:
            attempt += 1
            if attempt >= max_retries:
                raise PaymentError(f"Payment failed after {max_retries} attempts: {e}")
            time.sleep(backoff_factor)
    raise PaymentError("Retries exhausted")
