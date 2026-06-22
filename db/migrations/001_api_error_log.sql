-- Migration: add api_error_log to an EXISTING database.
-- init.sql only runs on a fresh Postgres volume, so run this once against
-- your live DB:  psql -U <user> -d finances -f db/migrations/001_api_error_log.sql
CREATE TABLE IF NOT EXISTS api_error_log (
    id SERIAL PRIMARY KEY,
    error_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50),
    endpoint VARCHAR(255),
    error_code VARCHAR(100),
    error_type VARCHAR(100),
    error_message TEXT,
    context TEXT
);
