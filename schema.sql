CREATE TABLE IF NOT EXISTS job_history
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended TIMESTAMP,
    succeeded BOOLEAN
);

-- not needed for now
-- CREATE INDEX IF NOT EXISTS job_history_started_idx ON job_history(started);
