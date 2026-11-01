CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    client_token TEXT NOT NULL,
    diff_hash TEXT NOT NULL,
    diff_text TEXT NOT NULL,
    file_paths TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('queued','running','done','failed')),
    verdict TEXT,
    report_md TEXT,
    error TEXT,
    is_demo INTEGER NOT NULL DEFAULT 0,
    is_replay INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    duration_s REAL
);

CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    severity TEXT NOT NULL,
    confidence TEXT NOT NULL,
    cwe TEXT NOT NULL DEFAULT '',
    file TEXT NOT NULL DEFAULT '',
    line INTEGER NOT NULL DEFAULT 0,
    evidence TEXT NOT NULL DEFAULT '',
    fix TEXT NOT NULL DEFAULT '',
    sources TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL CHECK(status IN ('kept','rejected')),
    rejection_reason TEXT
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    agent TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('idle','running','done','skipped','failed')),
    duration_s REAL NOT NULL DEFAULT 0,
    finding_count INTEGER NOT NULL DEFAULT 0,
    UNIQUE(review_id, agent)
);

CREATE TABLE IF NOT EXISTS review_logs (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    ts TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reviews_token_created
    ON reviews(client_token, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_token_hash
    ON reviews(client_token, diff_hash);
CREATE INDEX IF NOT EXISTS idx_reviews_queue
    ON reviews(status, created_at);
CREATE INDEX IF NOT EXISTS idx_findings_review
    ON findings(review_id, status);
CREATE INDEX IF NOT EXISTS idx_agent_runs_review
    ON agent_runs(review_id);
CREATE INDEX IF NOT EXISTS idx_review_logs_review
    ON review_logs(review_id, ts);
