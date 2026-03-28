-- migrations/2026-03-29-group-intervals.sql
ALTER TABLE groups ADD COLUMN interval_seconds INTEGER DEFAULT 300;
ALTER TABLE groups ADD COLUMN last_run_at TEXT;
