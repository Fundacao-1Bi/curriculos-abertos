CREATE TABLE IF NOT EXISTS "user" (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, "emailVerified" BOOLEAN NOT NULL DEFAULT FALSE,
  image TEXT, "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(), "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS session (
  id TEXT PRIMARY KEY, "expiresAt" TIMESTAMPTZ NOT NULL, token TEXT NOT NULL UNIQUE,
  "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(), "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  "ipAddress" TEXT, "userAgent" TEXT, "userId" TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS session_user_idx ON session("userId");
CREATE TABLE IF NOT EXISTS account (
  id TEXT PRIMARY KEY, "accountId" TEXT NOT NULL, "providerId" TEXT NOT NULL,
  "userId" TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  "accessToken" TEXT, "refreshToken" TEXT, "idToken" TEXT,
  "accessTokenExpiresAt" TIMESTAMPTZ, "refreshTokenExpiresAt" TIMESTAMPTZ, scope TEXT, password TEXT,
  "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(), "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE("providerId","accountId")
);
CREATE TABLE IF NOT EXISTS verification (
  id TEXT PRIMARY KEY, identifier TEXT NOT NULL, value TEXT NOT NULL, "expiresAt" TIMESTAMPTZ NOT NULL,
  "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(), "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS admin_roles (
  user_id TEXT PRIMARY KEY REFERENCES "user"(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK(role IN ('administrator','curator')),
  actor_type TEXT NOT NULL CHECK(actor_type IN ('human','automated')) DEFAULT 'automated'
);
CREATE TABLE IF NOT EXISTS audit_events (
  id UUID PRIMARY KEY, actor_id TEXT NOT NULL, actor_type TEXT NOT NULL CHECK(actor_type IN ('human','automated')),
  action TEXT NOT NULL, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, reason TEXT NOT NULL,
  before_data JSONB, after_data JSONB, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS audit_entity_idx ON audit_events(entity_type,entity_id,created_at);
CREATE TABLE IF NOT EXISTS jobs (
  id UUID PRIMARY KEY, type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','running','paused','succeeded','failed')),
  payload JSONB NOT NULL DEFAULT '{}', result JSONB, progress JSONB NOT NULL DEFAULT '{}', error TEXT,
  attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 3,
  idempotency_key TEXT UNIQUE, lease_owner TEXT, lease_until TIMESTAMPTZ, run_after TIMESTAMPTZ NOT NULL DEFAULT now(),
  pause_requested BOOLEAN NOT NULL DEFAULT FALSE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS jobs_ready_idx ON jobs(status,run_after,lease_until);
CREATE TABLE IF NOT EXISTS job_events (
  id BIGSERIAL PRIMARY KEY, job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  event JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS contributions (
  id UUID PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('error','source','relation')),
  record_url TEXT, record_id TEXT, description TEXT NOT NULL, evidence_url TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','accepted','rejected','needs_information')),
  decision_reason TEXT, decided_by TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS drafts (
  id UUID PRIMARY KEY, base_publication TEXT NOT NULL, title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'editing' CHECK(status IN ('editing','validated','prepared','published')),
  changes JSONB NOT NULL DEFAULT '[]', validation JSONB, prepared_publication TEXT,
  created_by TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS source_checks (
  id UUID PRIMARY KEY, source_id TEXT NOT NULL, publication_id TEXT, status TEXT NOT NULL,
  prior_hash TEXT, observed_hash TEXT, detail JSONB NOT NULL DEFAULT '{}', checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS source_checks_time_idx ON source_checks(source_id,checked_at DESC);
CREATE TABLE IF NOT EXISTS worker_heartbeats (
  id TEXT PRIMARY KEY, seen_at TIMESTAMPTZ NOT NULL DEFAULT now(), active_job UUID
);
CREATE TABLE IF NOT EXISTS request_metrics (
  bucket TIMESTAMPTZ NOT NULL, route TEXT NOT NULL, status INTEGER NOT NULL,
  requests BIGINT NOT NULL DEFAULT 0, total_ms DOUBLE PRECISION NOT NULL DEFAULT 0,
  PRIMARY KEY(bucket,route,status)
);
