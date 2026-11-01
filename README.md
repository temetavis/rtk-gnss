# RTK-GNSS Learning Sandbox

A hands-on sandbox for learning the technologies behind **GNSS positioning**,
**network RTK correction services**, and the **service platform** such a
business runs on — databases, APIs, automations, network monitoring, and
operations.

## What is covered

| Area | Where | What you learn |
|---|---|---|
| GNSS fundamentals | `docs/01-gnss-basics.md` | Pseudoranges, trilateration, error sources, DOP |
| RTK & network RTK | `docs/02-rtk-and-network-rtk.md` | Carrier phase, ambiguities, VRS, MAC, FKP concepts |
| NTRIP | `docs/03-ntrip.md` + `exercises/ntrip/` | The protocol correction streams ride on; a mock caster you can run |
| RTCM messages | `docs/04-rtcm-messages.md` + `exercises/rtcm/` | RTCM 3.x framing and parsing (1005 station coordinates) |
| Coordinate systems | `docs/05-coordinate-systems.md` + `exercises/coords/` | WGS84, ETRS89, EUREF-FIN, ENU, UTM, heights |
| RTK solver | `exercises/rtk_solver/` | A simplified single-baseline RTK engine, end to end |
| PostgreSQL | `docs/06-postgresql.md` + `exercises/db/` | Schema design, operational queries, PL/pgSQL triggers, psycopg |
| APIs & integrations | `docs/07-apis-and-integrations.md` + `exercises/api/`, `exercises/integrations/` | REST design, auth, webhooks, idempotent sync automations |
| Network monitoring | `docs/08-network-monitoring.md` + `exercises/monitoring/` | Check engine, flap suppression, auto-resolve, alerting |
| Service ops & security | `docs/09-service-ops.md` + `exercises/ops/` | Credential hygiene, config audit, infrastructure practice |

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# run all exercise tests (each exercise is self-verifying)
pytest

# run the mock NTRIP caster on localhost and connect a client
python3 -m exercises.ntrip.caster          # terminal 1
python3 -m exercises.ntrip.client          # terminal 2

# watch the RTK solver converge from float to fixed ambiguities
python3 -m exercises.rtk_solver.simulate

# run the station REST API (loopback only)
python3 -m exercises.api.service
```

### Optional: real PostgreSQL

The `exercises/db/` SQL is genuine PostgreSQL. With a Postgres available:

```bash
export DATABASE_URL="host=localhost port=5432 dbname=rtk user=rtk password=..."
psql "$DATABASE_URL" -f exercises/db/schema.sql
psql "$DATABASE_URL" -f exercises/db/migrations/001_add_health_flag.sql
```

Without `DATABASE_URL`, all exercises run against the portable in-process
store (`exercises/db/engine.py`), so the sandbox works anywhere.

## Suggested study order

1. **Positioning core**: `docs/01` → `exercises/rtk_solver/satellites.py`,
   then `docs/03` + the mock caster, then `docs/04` + the RTCM parser.
2. **High-accuracy**: `docs/02` → `exercises/rtk_solver/solver.py`
   (float → integer search → ratio test → fixed).
3. **Coordinates**: `docs/05` + `exercises/coords/`.
4. **Service platform**: `docs/06` → `exercises/db/` (schema, queries,
   PL/pgSQL trigger migration), `docs/07` → `exercises/api/` and
   `exercises/integrations/`, `docs/08` → `exercises/monitoring/`,
   `docs/09` → `exercises/ops/`.

Every module has tests in `tests/` — reading the tests is part of the
learning path: they encode the expected behavior of each piece.

## Real-world resources

- [RTKLIB](http://www.rtklib.com/) — open-source GNSS positioning library
- [NTRIP spec (RFC 9100)](https://www.rfc-editor.org/rfc/rfc9100)
- [RTCM standards](https://www.rtcm.org/) (SC-104 messages)
- [IGS network](https://igs.org/) — global reference station network
- [EUREF-FIN & Finnish national network (FGI)](https://www.maanmittauslaitos.fi/en/maps-and-spatial-data/positioning-services)
- [EGNOS / ESA Navipedia](https://gssc.esa.int/navipedia/) — excellent GNSS textbook online
- [PostgreSQL docs](https://www.postgresql.org/docs/) — start with the
  tutorial, then indexes, window functions, and PL/pgSQL
