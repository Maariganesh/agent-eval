# Regressive code: missing custom exceptions, uses bare except, swallows fatal errors
def execute_payment_with_retry(client_fn, idempotency_key, max_retries=3):
    for i in range(max_retries):
        try:
            print("Processing payment...")
            return client_fn(idempotency_key)
        except:
            pass
    return None
