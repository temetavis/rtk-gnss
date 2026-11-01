import pytest

from exercises.ops.security import (
    audit_service_config, generate_api_token, hash_password,
    token_fingerprint, verify_password, webhook_signature,
)


class TestPasswords:
    def test_hash_and_verify(self):
        stored = hash_password("correct horse battery")
        assert verify_password("correct horse battery", stored)
        assert not verify_password("wrong password", stored)

    def test_salting(self):
        a = hash_password("samepassword")
        b = hash_password("samepassword")
        assert a != b  # random salt -> different stored values
        assert verify_password("samepassword", a)
        assert verify_password("samepassword", b)


class TestApiTokens:
    def test_token_format(self):
        token = generate_api_token()
        assert token.startswith("rtk_")
        assert len(token) > 30

    def test_fingerprint_is_stable_and_not_reversible(self):
        token = generate_api_token()
        fp = token_fingerprint(token)
        assert fp == token_fingerprint(token)
        assert token not in fp
        assert len(fp) == 64  # sha256 hex


class TestConfigAudit:
    def test_insecure_config_finds_criticals(self):
        findings = audit_service_config({
            "ntrip_tls": False,
            "secret_in_repo": True,
            "default_admin_password": "admin123",
        })
        severities = {s for s, _ in findings}
        assert "critical" in severities

    def test_secure_config_is_clean(self):
        findings = audit_service_config({
            "ntrip_tls": True,
            "ssh_password_auth": False,
            "backups_tested": True,
            "dependency_scanning": True,
            "admin_2fa": True,
            "rate_limit_per_minute": 60,
        })
        assert findings == []

    def test_warnings_reported(self):
        findings = audit_service_config({
            "ntrip_tls": True,
            "backups_tested": False,
        })
        assert any(s == "warning" and "backup" in msg
                   for s, msg in findings)


def test_webhook_signature_deterministic():
    sig1 = webhook_signature("secret", b"payload")
    sig2 = webhook_signature("secret", b"payload")
    assert sig1 == sig2
    assert sig1 != webhook_signature("secret", b"other")
