# Service Operations, Security, and Infrastructure

Beyond feature work, this kind of role shares responsibility for running the
service: hardening, infrastructure maintenance with partners, and trying new
technology carefully.

## Security (together with partners)

Threat model first: what does an attacker gain from your service?

- **NTRIP credentials** → free correction service, reselling. Protect with
  hashed passwords, per-mountpoint entitlements, and rate limiting.
- **Customer data** (positions, usage) → privacy obligations (GDPR in the EU).
  Minimize what you store, and set retention policies.
- **Infrastructure access** → the biggest real risk. SSH keys + 2FA,
  no shared accounts, least-privilege service accounts, audit logs.

Practical security checklist for a small service:

1. TLS everywhere (NTRIP 2.0 supports it; legacy plain-HTTP casters are a
   known weakness — credentials travel in clear).
2. Secrets in a vault/secret manager, never in the repo or images.
3. Dependency scanning and prompt updates (GNSS/geo software is ordinary
   Python/Node/C in the end).
4. Backups with tested restores — a backup you have never restored is a hope,
   not a backup.
5. Incident response: who do you call, who may take the service down, and a
   written log of what happened.
6. Partner coordination: agree on shared responsibility (who patches the
   host OS, who owns the network, who handles DDoS mitigation).

## Server infrastructure (in cooperation with partners)

Typical shape for a Finnish positioning service:

- reference stations with routers/tunnels into the service network
- a Finnish/EU data center running the caster(s) and database
- monitoring and log aggregation
- deployment via CI/CD with staged rollout

Daily-ops skill set worth practicing:

- Linux server administration (systemd services, logs, disk/network triage)
- Nginx/HAProxy as TLS-terminating front end to the caster
- Docker/Podman packaging for reproducible deploys
- Infrastructure as code where possible (even a single Ansible playbook beats
  hand-edited servers)
- Capacity awareness: sessions per caster instance, DB growth from session
  logs and metrics (plan partitioning before it hurts)

## Trying new technologies without breaking the service

"Experimenting with new technologies" in a small team means **controlled
experiments**:

1. Prototype in a sandbox, never on production data flows.
2. Define the hypothesis ("can ephemeris preprocessing cut caster CPU 30%?").
3. Measure on realistic data before adopting.
4. Keep blast radius small: feature flags, staged rollout to a few
   mountpoints.
5. Write down the result — a short ADR (architecture decision record) turns
   an experiment into institutional knowledge.

## Improving existing systems

Practical patterns for legacy improvement:

- Add observability before changing behavior (you can't improve what you
  can't measure).
- Strangler-fig changes: route a slice of traffic through the new path,
  not a big-bang rewrite.
- Pay down the highest-risk item first (single point of failure, EOL
  dependency), not the most annoying one.

## Exercise pointers

- `exercises/ops/` — a tiny secrets/hygiene toolkit: API-key hashing with
  salted SHA-256 (learning stand-in for argon2), token generation, a
  checklist-style security audit function for service configs
- `tests/test_ops.py`
