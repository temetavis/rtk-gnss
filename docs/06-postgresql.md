# PostgreSQL for Positioning Services

A commercial RTK correction service is a database-backed business: stations,
accounts, mountpoints, subscriptions, session logs, and monitoring metrics all
live in relational storage. PostgreSQL is a typical choice.

## What the database holds

| Table | Contents |
|---|---|
| `reference_stations` | station metadata, ECEF/lat-lon coordinates, owner, status |
| `mountpoints` | NTRIP mountpoint name, format, linked station |
| `accounts` | NTRIP credentials, subscription level |
| `sessions` | who connected to which mountpoint, when, bytes sent |
| `station_observations` | per-station health metrics over time (noise, cycle slips) |
| `alerts` | monitoring alerts raised by automated checks |

Schema and queries live in `exercises/db/schema.sql` (genuine PostgreSQL DDL)
and `exercises/db/queries.sql`.

## PostgreSQL essentials worth practicing

- **JSONB** columns for flexible per-vendor metadata — plus GIN indexes on them.
- **PL/pgSQL functions** and triggers: e.g. automatically flag a station when
  its health metrics degrade (see `exercises/db/migrations/001_add_health_flag.sql`).
- **Views** for the operations dashboard: current station health, live sessions.
- **Window functions** for time series: "last observation per station",
  moving averages of cycle-slip counts.
- **Indexes**: partial and expression indexes; `EXPLAIN ANALYZE` everything.
- **Backups/PITR**: `pg_dump` is not enough for production — learn WAL
  archiving and point-in-time recovery concepts.
- **Connection pooling**: services talk to Postgres through a pooler
  (PgBouncer) so caster workers don't open thousands of raw connections.

## Using the exercises

The SQL files are real PostgreSQL. Two ways to run them:

1. **With a real Postgres** (recommended):
   ```bash
   export DATABASE_URL="host=localhost port=5432 dbname=rtk user=rtk password=..."
   psql "$DATABASE_URL" -f exercises/db/schema.sql
   pytest tests/test_db.py          # integration tests, skipped if no DB
   ```
2. **Without Postgres**: `exercises/db/engine.py` implements a small
   SQL-compatible store used by the other exercises (API, monitoring), so the
   whole sandbox still runs and self-verifies anywhere.

## psycopg (the modern Python driver)

```python
import psycopg
with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM reference_stations WHERE status = %s",
                    ("online",))
        rows = cur.fetchall()
```

Key habits: always parameterize (never f-string SQL), use connection pools in
long-running services, and keep transactions short.

## Exercise pointers

- `exercises/db/engine.py` — the in-memory store with a psycopg-like API
- `exercises/db/queries.py` — named queries the service layer uses
- `tests/test_db.py` — runs against a real Postgres when `DATABASE_URL` is set,
  otherwise against the portable engine
