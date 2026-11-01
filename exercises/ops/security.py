"""Security hygiene toolkit: credential hashing, API tokens, config audit.

Learning stand-ins for production practice:
- hashing here uses salted SHA-256 for clarity; real services use argon2/bcrypt
- token generation follows the "show once, store hash" rule for API keys
"""

import hashlib
import hmac
import os
import secrets


def hash_password(password: str, salt: bytes = None) -> str:
    """Salted hash; returns 'salt$hexdigest' (argon2/bcrypt in production)."""
    salt = salt or os.urandom(16)
    digest = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
    return f"{salt.hex()}${digest}"


def verify_password(password: str, stored: str) -> bool:
    salt_hex, digest = stored.split("$", 1)
    salt = bytes.fromhex(salt_hex)
    expected = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(expected, digest)


def generate_api_token(prefix: str = "rtk") -> str:
    """Opaque bearer token, shown to the customer exactly once."""
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def token_fingerprint(token: str) -> str:
    """What you store: a hash of the token, never the token itself."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def audit_service_config(config: dict) -> list:
    """Checklist-style security audit of a service config dict.

    Returns a list of findings: (severity, description).
    """
    findings = []
    if config.get("ntrip_tls") is not True:
        findings.append(("critical",
                         "NTRIP endpoint should require TLS; plain HTTP "
                         "sends Basic credentials in the clear"))
    if config.get("secret_in_repo"):
        findings.append(("critical",
                         "secrets committed to the repository"))
    if config.get("default_admin_password"):
        findings.append(("critical", "default admin password still set"))
    if config.get("ssh_password_auth") is not False:
        findings.append(("warning",
                         "SSH password authentication should be disabled"))
    if config.get("backups_tested") is not True:
        findings.append(("warning",
                         "backup restore has never been tested"))
    if config.get("dependency_scanning") is not True:
        findings.append(("warning",
                         "no automated dependency vulnerability scanning"))
    if config.get("admin_2fa") is not True:
        findings.append(("warning", "admin accounts lack two-factor auth"))
    if config.get("rate_limit_per_minute") is None:
        findings.append(("warning",
                         "no rate limiting on public endpoints"))
    return findings


def webhook_signature(secret: str, payload: bytes) -> str:
    """HMAC-SHA256 signature for outgoing webhooks."""
    return hmac.new(secret.encode("utf-8"), payload,
                    hashlib.sha256).hexdigest()
