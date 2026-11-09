# Service Health Dashboard — mock RTK provider monitoring

Commercial RTK correction services are exactly that: *services*. Beyond the
GNSS math, an operations team has to watch the health of the whole chain —
reference stations, caster mountpoints, correction latency, and connected
rovers. This exercise builds a **mock mobile web dashboard** for that job,
in the same spirit as the mock NTRIP caster in `exercises/ntrip/`.

## What a provider actually monitors

| Signal | Why it matters |
|---|---|
| Station up/down | A silent reference station means no corrections for its area |
| Correction latency | RTK needs corrections within a few seconds; >5 s degrades to float |
| Messages per minute | RTCM streams send ~1 message per type per second |
| Rover sessions | Connected clients per mountpoint — capacity and revenue |
| 24 h uptime | SLA reporting |

Rules of thumb used by the mock (see `service.py`):

- **healthy** — latency under 2 s, streaming, no recent outage
- **degraded** — latency 2–5 s, or an outage inside the last hour
- **down** — no data received for over 60 s

## The pieces

```
exercises/dashboard/
  service.py   deterministic health model (stations, latency, outages)
  ui.py        mobile-first single-page dashboard (HTML/CSS/JS in one string)
  app.py       loopback-only HTTP server: GET / and GET /api/health
```

The model is seeded per minute, so any single fetch is reproducible for
tests, while a live page still evolves as the clock advances.

## Run it

```bash
python3 -m exercises.dashboard.app     # binds 127.0.0.1:8000 only
```

Open <http://127.0.0.1:8000/> — narrow the browser window to phone width to
see the mobile layout. The page polls `/api/health` every 5 s and re-renders
the status cards.

Try the forced-outage seed to see a red dashboard:

```bash
python3 -c "from exercises.dashboard.app import serve; serve(seed='demo-outage')"
```

## Things to study / extend

1. `service.py::classify` — the status state machine; add a "recovering"
   state for stations that just came back.
2. `ui.py` — no framework, no build step: `fetch` + template literals.
   Add a sparkline of latency history using a rolling buffer.
3. `app.py` — `ThreadingHTTPServer` and `BaseHTTPRequestHandler`; add a
   `/api/history` endpoint that returns the last N snapshots.
4. Wire it to the real mock caster: import `exercises.ntrip.caster` state
   instead of the synthetic model.

## Real-world parallels

- NTRIP caster admin pages (e.g. BKG caster status endpoints)
- Cloud monitoring dashboards (Grafana, Cloudwatch) fed by station telemetry
- The [EUREF/IPN networks](https://igs.org/) station status pages
