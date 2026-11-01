-- 001_add_health_flag.sql
-- PL/pgSQL + trigger exercise: automatically flag a station as 'degraded'
-- when its stream goes stale or noise spikes, and back to 'online' when it
-- recovers. Migrations like this are how schema and behavior evolve in
-- controlled, reviewable steps.

CREATE OR REPLACE FUNCTION station_health_trigger() RETURNS trigger AS $$
DECLARE
    station record;
BEGIN
    SELECT status INTO station FROM reference_stations WHERE id = NEW.station_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'unknown station %', NEW.station_id;
    END IF;

    IF NEW.stream_age_s > 15 THEN
        UPDATE reference_stations SET status = 'degraded' WHERE id = NEW.station_id;
        INSERT INTO alerts (station_id, kind, severity, details)
        VALUES (NEW.station_id, 'stale_stream', 'warning',
                jsonb_build_object('stream_age_s', NEW.stream_age_s));
    ELSIF NEW.stream_age_s < 5 AND NEW.phase_noise_mm < 3.0
          AND station.status = 'degraded' THEN
        UPDATE reference_stations SET status = 'online' WHERE id = NEW.station_id;
        UPDATE alerts
           SET state = 'resolved', resolved_at = now()
         WHERE station_id = NEW.station_id AND kind = 'stale_stream'
           AND state = 'firing';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_station_health
AFTER INSERT ON station_metrics
FOR EACH ROW EXECUTE FUNCTION station_health_trigger();
