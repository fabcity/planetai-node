-- Two tables and a view. Add a third table only when a service forces you to.

CREATE TABLE IF NOT EXISTS sensors (
  sensor_id TEXT PRIMARY KEY,           -- 'sc-19880' | 'bad-pa-46949' | 'ag-<serial>' ...
  source    TEXT NOT NULL,              -- 'smartcitizen' | 'baliairdispatch' | 'airgradient' ...
  name      TEXT,
  lat       DOUBLE PRECISION,
  lon       DOUBLE PRECISION,
  indoor    BOOLEAN NOT NULL DEFAULT FALSE,
  local     BOOLEAN NOT NULL DEFAULT FALSE,   -- TRUE = physically at this node (ours). FALSE = reference/context.
  meta      JSONB
);

CREATE TABLE IF NOT EXISTS readings (
  ts        TIMESTAMPTZ NOT NULL,
  sensor_id TEXT NOT NULL REFERENCES sensors(sensor_id),
  metric    TEXT NOT NULL,              -- pm25 | pm25_raw | pm10 | pm1 | temp | humidity | pressure | aqi ...
  value     DOUBLE PRECISION NOT NULL,
  UNIQUE (sensor_id, metric, ts)        -- polling twice never duplicates
);
CREATE INDEX IF NOT EXISTS readings_lookup ON readings (sensor_id, metric, ts DESC);

CREATE TABLE IF NOT EXISTS alerts (
  id        BIGSERIAL PRIMARY KEY,
  ts        TIMESTAMPTZ NOT NULL DEFAULT now(),
  rule_id   TEXT NOT NULL,
  sensor_id TEXT,
  level     TEXT,
  text      TEXT
);
CREATE INDEX IF NOT EXISTS alerts_cooldown ON alerts (rule_id, sensor_id, ts DESC);

-- The ρ instrument. A human (or an app on their behalf) records what happened after an alert.
-- stage: acknowledged (someone saw it) · acted (someone did the thing) · measured (the outcome was checked)
CREATE TABLE IF NOT EXISTS actions (
  ts        TIMESTAMPTZ NOT NULL DEFAULT now(),
  alert_id  BIGINT REFERENCES alerts(id),
  stage     TEXT NOT NULL CHECK (stage IN ('acknowledged','acted','measured')),
  actor     TEXT,
  note      TEXT
);

-- Hourly means. A plain view is fine until this node holds millions of rows; then materialize it.
CREATE OR REPLACE VIEW readings_1h AS
SELECT date_trunc('hour', ts) AS bucket, sensor_id, metric,
       avg(value) AS mean, min(value) AS min, max(value) AS max, count(*) AS n
FROM readings GROUP BY 1, 2, 3;

-- Rolling stats per sensor/metric, used by rules. One row per (sensor, metric).
CREATE OR REPLACE VIEW stats AS
SELECT r.sensor_id, r.metric, s.indoor, s.local, s.lat, s.lon, s.name,
       (array_agg(r.value ORDER BY r.ts DESC))[1]                          AS last,
       max(r.ts)                                                             AS last_ts,
       extract(epoch FROM now() - max(r.ts)) / 60                            AS silent_minutes,
       avg(r.value) FILTER (WHERE r.ts > now() - interval '15 minutes')      AS mean_15m,
       avg(r.value) FILTER (WHERE r.ts > now() - interval '1 hour')          AS mean_1h,
       avg(r.value) FILTER (WHERE r.ts > now() - interval '24 hours')        AS mean_24h
FROM readings r JOIN sensors s USING (sensor_id)
WHERE r.ts > now() - interval '24 hours'
GROUP BY r.sensor_id, r.metric, s.indoor, s.local, s.lat, s.lon, s.name;
