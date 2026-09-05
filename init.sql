-- The whole schema, in one idempotent file.
-- Postgres runs this automatically only when the data volume is first created. `./update.sh` applies the SAME file
-- to an existing database on every update — that is why every statement here must be safe to run twice.
-- Rules: CREATE TABLE IF NOT EXISTS · ALTER TABLE ADD COLUMN IF NOT EXISTS · DROP VIEW then CREATE (column
-- lists change between versions, and CREATE OR REPLACE VIEW cannot reorder columns).

CREATE TABLE IF NOT EXISTS sensors (
  sensor_id TEXT PRIMARY KEY,           -- 'sc-19880' | 'bad-pa-46949' | 'ag-<serial>' ...
  source    TEXT NOT NULL,              -- 'smartcitizen' | 'baliairdispatch' | 'airgradient' ...
  name      TEXT,
  lat       DOUBLE PRECISION,
  lon       DOUBLE PRECISION,
  indoor    BOOLEAN NOT NULL DEFAULT FALSE,
  local     BOOLEAN NOT NULL DEFAULT FALSE,   -- TRUE = physically at this node (ours). FALSE = reference/context.
  kind      TEXT NOT NULL DEFAULT 'sensor',   -- sensor | portal | model | survey | child   (how the number was produced)
  scale     TEXT NOT NULL DEFAULT 'community',-- community | city | region | bioregion | planet  (what the number describes)
  cadence   TEXT,                             -- 'PT5M' | 'P1D' | 'P1Y' — how often it can meaningfully change
  meta      JSONB
);
-- additive for nodes created before v0.3
ALTER TABLE sensors ADD COLUMN IF NOT EXISTS kind    TEXT NOT NULL DEFAULT 'sensor';
ALTER TABLE sensors ADD COLUMN IF NOT EXISTS scale   TEXT NOT NULL DEFAULT 'community';
ALTER TABLE sensors ADD COLUMN IF NOT EXISTS cadence TEXT;

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
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS id BIGSERIAL;
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
DROP VIEW IF EXISTS readings_1h CASCADE;
CREATE VIEW readings_1h AS
SELECT date_trunc('hour', ts) AS bucket, sensor_id, metric,
       avg(value) AS mean, min(value) AS min, max(value) AS max, count(*) AS n
FROM readings GROUP BY 1, 2, 3;

-- Rolling stats per sensor/metric, used by rules. One row per (sensor, metric).
DROP VIEW IF EXISTS stats CASCADE;
CREATE VIEW stats AS
SELECT r.sensor_id, r.metric, s.indoor, s.local, s.kind, s.scale, s.lat, s.lon, s.name,
       (array_agg(r.value ORDER BY r.ts DESC))[1]                          AS last,
       max(r.ts)                                                             AS last_ts,
       extract(epoch FROM now() - max(r.ts)) / 60                            AS silent_minutes,
       avg(r.value) FILTER (WHERE r.ts > now() - interval '15 minutes')      AS mean_15m,
       avg(r.value) FILTER (WHERE r.ts > now() - interval '1 hour')          AS mean_1h,
       avg(r.value) FILTER (WHERE r.ts > now() - interval '24 hours')        AS mean_24h
FROM readings r JOIN sensors s USING (sensor_id)
-- rolling stats are for sensors only; slow sources (portals, models) live in the `observations` view
WHERE r.ts > now() - interval '24 hours' AND s.kind = 'sensor'
GROUP BY r.sensor_id, r.metric, s.indoor, s.local, s.kind, s.scale, s.lat, s.lon, s.name;

-- Slow-moving numbers (a city statistic, a satellite point sample, a survey) don't belong in a 24h rolling view.
-- One row per source per metric per period, latest wins.
DROP VIEW IF EXISTS observations CASCADE;
CREATE VIEW observations AS
SELECT DISTINCT ON (r.sensor_id, r.metric)
       r.sensor_id, r.metric, r.value, r.ts, s.name, s.kind, s.scale, s.local, s.cadence, s.meta
FROM readings r JOIN sensors s USING (sensor_id)
WHERE s.kind <> 'sensor'
ORDER BY r.sensor_id, r.metric, r.ts DESC;

-- Where this node's schema is. Read by update.sh and reported at /health.
CREATE TABLE IF NOT EXISTS schema_version (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now());
INSERT INTO schema_version (version) VALUES ('0.4') ON CONFLICT DO NOTHING;
INSERT INTO schema_version (version) VALUES ('0.14') ON CONFLICT DO NOTHING;

-- Settings the GUI can change while the node runs. Overlays .env: a key here wins over the environment.
-- Bootstrap-only keys (ports, database, compose profiles) stay in .env; the app lists which is which.
CREATE TABLE IF NOT EXISTS settings (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
