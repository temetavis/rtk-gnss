import pytest

from exercises.db.engine import MemoryStore
from exercises.integrations.feed_sync import FeedSync
from exercises.integrations.webhooks import (
    WebhookRetryPolicy, build_event, sign, verify,
)


class TestFeedSync:
    @pytest.fixture
    def feed(self):
        return [
            {"code": "HEL1", "name": "Helsinki 1", "lat": 60.17,
             "lon": 24.94, "owner": "partner-a", "status": "online"},
            {"code": "TKU1", "name": "Turku 1", "lat": 60.45,
             "lon": 22.27, "owner": "partner-a", "status": "online"},
        ]

    def test_creates_new_stations(self, feed):
        sync = FeedSync(MemoryStore())
        report = sync.sync_stations(feed)
        assert report["created"] == ["HEL1", "TKU1"]
        assert report["unchanged"] == []

    def test_idempotent_rerun(self, feed):
        sync = FeedSync(MemoryStore())
        sync.sync_stations(feed)
        report = sync.sync_stations(feed)  # same feed again
        assert report["created"] == []
        assert report["updated"] == []
        assert sorted(report["unchanged"]) == ["HEL1", "TKU1"]

    def test_detects_changes(self, feed):
        sync = FeedSync(MemoryStore())
        sync.sync_stations(feed)
        feed[0]["name"] = "Helsinki main"
        feed[0]["status"] = "degraded"
        report = sync.sync_stations(feed)
        assert report["updated"][0]["code"] == "HEL1"
        assert set(report["updated"][0]["changed"]) == {"name", "status"}


class TestWebhooks:
    SECRET = "whsec_test"

    def test_sign_verify_roundtrip(self):
        payload, headers = build_event("station.outage",
                                       {"station": "HEL1"}, self.SECRET)
        assert verify(self.SECRET, payload,
                      headers["X-Webhook-Signature"]) is True

    def test_tampered_payload_rejected(self):
        payload, headers = build_event("station.outage",
                                       {"station": "HEL1"}, self.SECRET)
        tampered = payload.replace(b"HEL1", b"TKU1")
        assert verify(self.SECRET, tampered,
                      headers["X-Webhook-Signature"]) is False

    def test_wrong_secret_rejected(self):
        payload, headers = build_event("station.outage",
                                       {"station": "HEL1"}, self.SECRET)
        assert verify("whsec_other", payload,
                      headers["X-Webhook-Signature"]) is False

    def test_replayed_old_signature_rejected(self):
        payload = b'{"type": "test"}'
        old = sign(self.SECRET, payload, timestamp=1)  # epoch
        assert verify(self.SECRET, payload, old) is False

    def test_malformed_signature_rejected(self):
        assert verify(self.SECRET, b"{}", "not-a-signature") is False


class TestRetryPolicy:
    def test_exponential_backoff(self):
        policy = WebhookRetryPolicy(base_delay_s=5, factor=2)
        assert policy.delay_for(1) == 5
        assert policy.delay_for(2) == 10
        assert policy.delay_for(3) == 20

    def test_dead_letter_threshold(self):
        policy = WebhookRetryPolicy(max_attempts=5)
        assert policy.should_dead_letter(4) is False
        assert policy.should_dead_letter(5) is True
