"""Signed webhooks: how a service notifies partner systems of events."""

import hashlib
import hmac
import json
import time


def sign(secret: str, payload: bytes, timestamp: int = None) -> str:
    """HMAC-SHA256 over 'timestamp.payload' (replay protection)."""
    ts = timestamp if timestamp is not None else int(time.time())
    message = f"{ts}.".encode("utf-8") + payload
    digest = hmac.new(secret.encode("utf-8"), message,
                      hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


def verify(secret: str, payload: bytes, signature: str,
           tolerance_s: int = 300) -> bool:
    """Verify a webhook signature, rejecting old timestamps (replay)."""
    try:
        parts = dict(p.split("=", 1) for p in signature.split(","))
        ts, v1 = int(parts["t"]), parts["v1"]
    except (KeyError, ValueError):
        return False
    if abs(int(time.time()) - ts) > tolerance_s:
        return False
    message = f"{ts}.".encode("utf-8") + payload
    expected = hmac.new(secret.encode("utf-8"), message,
                        hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)


def build_event(event_type: str, data: dict, secret: str):
    """Produce (payload_bytes, headers) for an outgoing webhook."""
    payload = json.dumps({"type": event_type, "data": data},
                         sort_keys=True).encode("utf-8")
    signature = sign(secret, payload)
    return payload, {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
    }


class WebhookRetryPolicy:
    """Exponential backoff with a dead-letter threshold.

    In production this is a queue worker; here it just computes schedules
    so the policy itself can be tested.
    """

    def __init__(self, base_delay_s=5, factor=2, max_attempts=5):
        self.base_delay = base_delay_s
        self.factor = factor
        self.max_attempts = max_attempts

    def delay_for(self, attempt: int) -> int:
        """Delay before retry `attempt` (1-based)."""
        return self.base_delay * (self.factor ** (attempt - 1))

    def should_dead_letter(self, attempt: int) -> bool:
        return attempt >= self.max_attempts
