ALTER TABLE publications ADD COLUMN storage_format text NOT NULL DEFAULT 'embedded-v1';
ALTER TABLE publications ADD COLUMN artifact_manifest_sha256 text;
-- Existing snapshots remain byte/semantically intact. New national snapshots keep only metadata here;
-- canonical item and relation payloads live in the immutable relational tables.
