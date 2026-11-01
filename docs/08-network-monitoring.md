# Automatic Network Monitoring

A reference station network is only as good as its uptime. "Automatic network
monitoring" means software that continuously checks every station and raises
actionable alerts — so outages are noticed in minutes, not by customer calls.

## What to monitor on a reference station

| Signal | Meaning | Alert when |
|---|---|---|
| stream age | seconds since last RTCM data | > 10–15 s (link down) |
| observations/epoch | satellite count in the stream | low for the time of day |
| cycle slips per minute | signal quality indicator | spikes above baseline |
| carrier noise (phase RMS) | receiver/antenna health | degraded vs 24h baseline |
| coordinate stability | derived position vs known coords | drift (antenna moved!) |
| latency end-to-end | caster→rover delivery | growing trend |

## Monitoring loop anatomy

```
poller ──metrics──> time-series store ──> check engine ──> alerter ──> on-call
   │                                                            │
   └─────────────── recent metrics ◀── dashboard ◀─────────────┘
```

1. **Poller**: queries each station's latest data (from the DB or the caster).
2. **Check engine**: evaluates rules against thresholds and *baselines*
   (compare with the same hour over previous days, not a fixed constant —
   satellite visibility varies with time of day).
3. **Alerter**: raises alerts with severity, deduplicates (don't page twice
   for the same incident), and resolves them automatically when values
   recover.
4. **Escalation**: unacknowledged critical alerts escalate after X minutes.

## Alert quality: the real skill

- **One alert per incident**, not per data point. Track alert state
  (firing/resolved) in the DB.
- **Flap suppression**: require N consecutive bad checks before firing, and
  require recovery for M checks before resolving. Otherwise a flaky link
  pages you all night.
- **Severity discipline**: only true emergencies page; the rest goes to
  dashboards and daily reports.
- **Runbooks**: every alert type should point to a documented check list.

## SQL + monitoring

The queries that power dashboards ("last observation per station",
"stations with no data for 5 minutes", "cycle-slip rate vs last week") are
window functions and time-bucket aggregates — see
`exercises/db/queries.sql` and the `queries.py` module.

## Exercise pointers

- `exercises/monitoring/checks.py` — check engine with thresholds,
  flap suppression, and auto-resolve
- `exercises/monitoring/poller.py` — polls the station store, writes metrics
- `exercises/monitoring/alerts.py` — alert objects, severity, dedup
- `tests/test_monitoring.py` — drives a simulated station outage end to end
