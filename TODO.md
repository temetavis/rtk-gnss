# TODO — Local Machine Exercises

Things worth doing on your own machine that the sandbox can't cover:
real hardware, live public services, and full-size software stacks.

## Real NTRIP in the wild

- [ ] Connect to a **free public NTRIP caster** (e.g. ONOCOY, RTK2go, or a
      national sample mountpoint) with a real rover or a software client, and
      watch actual RTCM 3 traffic with the knowledge from `exercises/ntrip/`
      and `exercises/rtcm/`
- [ ] Point this repo's client (`python3 -m exercises.ntrip.client`) at a real
      caster URL to see how implementations differ (NTRIP 1.0 vs 2.0 quirks,
      chunked responses, redirect handling)
- [ ] Capture a few minutes of a real RTCM stream to a file, then decode it
      locally: extend `exercises/rtcm/` with parsers for MSM4/MSM6 (107x/108x)
      messages and plot satellite counts over time
- [ ] Register for a trial of a commercial Finnish/EU network RTK service and
      compare its sourcetable, GGA round-trip behavior, and correction latency
      against the mock caster

## Real receivers and hardware

- [ ] Borrow/buy a **u-blox or dual-band GNSS receiver** (even a ~€30 u-blox
      NEO-M8T/M9T evaluation board works) and read raw NMEA + UBX via serial
- [ ] Log raw receiver output to RINEX with `rtklib` or `teqc`, then process
      a real static baseline in RTKLIB (RTKPOST) and compare float vs fixed
      solutions — the same pipeline as `exercises/rtk_solver/`, but with real
      ionosphere/multipath
- [ ] If you can access an RTK-capable rover (Emlid Reach, Juniper, Stonex,
      etc.): do a stakeout or a known-point check with network RTK corrections
      and write down the observed accuracy vs the simulated ~1.7 cm
- [ ] Test what actually breaks RTK in the field: mask angle under trees,
      multipath near a wall, lost cellular data (watch time-to-re-fix)
- [ ] Feed a software GNSS SDR capture (e.g. a GPS L1 sample file) through
      a tracking program to see the correlation/code/carrier machinery under
      the observation equations

## Real PostgreSQL

- [ ] Install PostgreSQL locally, apply `exercises/db/schema.sql` and the
      PL/pgSQL migration, and run the test suite with `DATABASE_URL` set —
      then compare execution plans with `EXPLAIN ANALYZE` on
      `exercises/db/queries.sql`
- [ ] Load synthetic metrics (write a small generator, 10M+ rows in
      `station_metrics`) and practice: partitioning by time, BRIN vs B-tree
      index behavior, and how "latest metric per station" performs at scale
- [ ] Set up WAL archiving + point-in-time recovery, then actually restore
      a dropped table (a backup you haven't restored is just hope)
- [ ] Run PgBouncer in front of your database and simulate many concurrent
      caster clients to see pooling behavior

## Production-grade service stack

- [ ] Recreate `exercises/api/` endpoints in **FastAPI + Pydantic**, with
      OpenAPI docs generated, and compare the ergonomics against the
      stdlib-only version in the repo
- [ ] Put the mock NTRIP caster behind **nginx/HAProxy with TLS** (self-signed
      is fine) and verify NTRIP 2.0 over TLS from a real rover app
- [ ] Containerize the caster + API + PostgreSQL with Docker Compose, then
      add Prometheus metrics to the monitoring poller and graph alert rates
      in Grafana
- [ ] Schedule the feed-sync job with a real runner (cron, systemd timers,
      or a queue like Celery/RQ) and test idempotency after killing the job
      mid-run
- [ ] Practice an incident: shut down the "reference station" feed, measure
      detection time from poller to alert, and tune `fire_after`/severity
      until it pages fast without flapping

## Reading & tools to install locally

- [ ] RTKLIB (GUI + CLI), its manual is a practical education in itself
- [ ] `teqc` and gfzrnx for RINEX manipulation and QC
- [ ] ESA Navipedia cover-to-cover for the theory gaps
- [ ] BKG's NTRIP caster/professional documentation for the operational side
- [ ] PostgreSQL docs: partitioning, window functions, PL/pgSQL chapters
