-- Reference station network schema (PostgreSQL)
-- Used by the service layer, API, and monitoring exercises.

CREATE TABLE IF NOT EXISTS reference_stations (
    id          SERIAL PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    owner       TEXT NOT NULL DEFAULT '',
    lat         DOUBLE PRECISION NOT NULL,
    lon         DOUBLE PRECISION NOT NULL,
    h_ecef_x    DOUBLE PRECISION NOT NULL,
    h_ecef_y    DOUBLE PRECISION NOT NULL,
    h_ecef_z    DOUBLE PRECISION NOT NULL,
    status      TEXT NOT NULL DEFAULT 'online'
                CHECK (status IN ('online', 'degraded', 'offline', 'maintenance')),
    metadata    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mountpoints (
    id            SERIAL PRIMARY KEY,
    station_id    INTEGER NOT NULL REFERENCES reference_stations(id),
    name          TEXT NOT NULL UNIQUE,
    format        TEXT NOT NULL DEFAULT 'RTCM 3.2',
    nav_systems   TEXT NOT NULL DEFAULT 'GPS+GLO+GAL',
    requires_gga  BOOLEAN NOT NULL DEFAULT TRUE,
    active        BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS accounts (
    id                SERIAL PRIMARY KEY,
    username          TEXT NOT NULL UNIQUE,
    password_hash     TEXT NOT NULL,
    subscription      TEXT NOT NULL DEFAULT 'standard'
                      CHECK (subscription IN ('trial', 'standard', 'pro')),
    api_token_hash    TEXT,
    active            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
    id            BIGSERIAL PRIMARY KEY,
    account_id    INTEGER NOT NULL REFERENCES accounts(id),
    mountpoint    TEXT NOT NULL,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at      TIMESTAMPTZ,
    bytes_sent    BIGINT NOT NULL DEFAULT 0,
    rover_lat     DOUBLE PRECISION,
    rover_lon     DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS station_metrics (
    id             BIGSERIAL PRIMARY KEY,
    station_id     INTEGER NOT NULL REFERENCES reference_stations(id),
    recorded_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    stream_age_s   DOUBLE PRECISION NOT NULL,
    sats_tracked   INTEGER NOT NULL,
    cycle_slips    INTEGER NOT NULL,
    phase_noise_mm DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_metrics_station_time
    ON station_metrics (station_id, recorded_at DESC);

-- Alerts raised by the monitoring system; state machine: firing -> resolved
CREATE TABLE IF NOT EXISTS alerts (
    id           BIGSERIAL PRIMARY KEY,
    station_id   INTEGER NOT NULL REFERENCES reference_stations(id),
    kind         TEXT NOT NULL,
    severity     TEXT NOT NULL CHECK (severity IN ('warning', 'critical')),
    details      JSONB NOT NULL DEFAULT '{}',
    raised_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at  TIMESTAMPTZ,
    state        TEXT NOT NULL DEFAULT 'firing'
                 CHECK (state IN ('firing', 'resolved'))
);
