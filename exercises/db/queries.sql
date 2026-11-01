-- Operational queries for the station network (PostgreSQL)
-- Practice targets: window functions, time buckets, partial predicates.

-- Last metric per station ("gaps and latest" pattern)
SELECT DISTINCT ON (station_id)
    station_id, recorded_at, stream_age_s, sats_tracked, cycle_slips
FROM station_metrics
ORDER BY station_id, recorded_at DESC;

-- Stations with no fresh data (potential outage)
SELECT s.code, s.name
FROM reference_stations s
WHERE s.status = 'online'
  AND NOT EXISTS (
      SELECT 1 FROM station_metrics m
      WHERE m.station_id = s.id
        AND m.recorded_at > now() - INTERVAL '2 minutes'
  );

-- Cycle-slip rate now vs same hour yesterday (baseline comparison)
SELECT
    now_window.station_id,
    now_window.slips AS slips_now,
    base_window.slips AS slips_baseline
FROM (
    SELECT station_id, avg(cycle_slips)::float AS slips
    FROM station_metrics
    WHERE recorded_at > now() - INTERVAL '15 minutes'
    GROUP BY station_id
) now_window
JOIN LATERAL (
    SELECT avg(cycle_slips)::float AS slips
    FROM station_metrics
    WHERE station_id = now_window.station_id
      AND recorded_at BETWEEN now() - INTERVAL '24 hours' - INTERVAL '15 minutes'
                          AND now() - INTERVAL '24 hours'
) base_window ON TRUE;

-- Firing alerts with station code, for the on-call dashboard
SELECT s.code, a.kind, a.severity, a.raised_at
FROM alerts a
JOIN reference_stations s ON s.id = a.station_id
WHERE a.state = 'firing'
ORDER BY a.raised_at DESC;

-- Usage per mountpoint over the last day (bytes and sessions)
SELECT mountpoint, count(*) AS sessions, sum(bytes_sent) AS bytes
FROM sessions
WHERE started_at > now() - INTERVAL '1 day'
GROUP BY mountpoint
ORDER BY bytes DESC;
