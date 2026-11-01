# APIs and Integrations

The correction service doesn't live alone: customer systems, partner
platforms, billing, and monitoring dashboards all need **defined interfaces**
to talk to it. Two broad categories appear in this kind of role:

1. **APIs you expose** — REST/JSON endpoints for customers and internal tools.
2. **Integrations you build** — scheduled automations between systems you use
   (reference station data feeds, account provisioning, invoice exports),
   often implemented as background jobs.

## REST API design for a positioning service

Resources map naturally to the domain:

```
GET    /api/v1/stations                 list reference stations
GET    /api/v1/stations/{id}            station detail + status
GET    /api/v1/stations/{id}/health      recent health metrics
POST   /api/v1/accounts                 create NTRIP credentials
GET    /api/v1/sessions?active=true     live sessions
```

Versioning in the path (`/v1`), JSON bodies, standard status codes
(400 validation, 401 auth, 404 unknown, 409 conflict, 422 semantic error).

## Authentication patterns

| Method | Use |
|---|---|
| API keys (bearer tokens) | machine-to-machine, customer integrations |
| Basic auth | (still used by NTRIP itself) |
| mTLS / signed requests | high-security partner integrations |
| OAuth2 client credentials | larger partner platforms |

Never store raw credentials: store salted hashes (argon2/bcrypt) for
passwords, and a token hash for API keys so a leaked database doesn't leak
working keys.

## Automations between systems

"Automations between the software we use" typically means:

- **Scheduled jobs**: sync reference station metadata from partner feeds into
  your DB nightly; export usage reports to billing.
- **Event-driven**: new account provisioned → credentials pushed to the
  caster → welcome email queued.
- **Idempotency**: every automation must survive being run twice — dedupe on
  external IDs, use `INSERT ... ON CONFLICT DO NOTHING` patterns.

## Webhooks

Outgoing webhooks notify partners of events (station outage, subscription
change). Rules of thumb: signed payloads (HMAC), retries with exponential
backoff, and a dead-letter queue after N failures. The receiver must verify
the signature before trusting the payload.

## Practical stack notes

- Small, standard library HTTP services are fine to learn with — see
  `exercises/api/service.py` (loopback-only, no frameworks).
- In production teams typically use FastAPI/Flask + Pydantic, Celery/RQ for
  background jobs, and OpenAPI docs generated from code.
- Keep API logic thin: validate → call service layer → serialize. Business
  rules live in the service/database layer, not in route handlers.

## Exercise pointers

- `exercises/api/service.py` — REST API over the station database with
  token auth, JSON validation, and proper status codes
- `exercises/integrations/webhooks.py` — HMAC-signed webhook sender/receiver
- `exercises/integrations/feed_sync.py` — idempotent partner-data sync job
- `tests/test_api.py`, `tests/test_integrations.py`
