CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    client_token TEXT NOT NULL,
    diff_hash TEXT NOT NULL,
    diff_text TEXT NOT NULL,
    file_paths TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'web',
    status TEXT NOT NULL,
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

CREATE INDEX IF NOT EXISTS idx_reviews_client_created
    ON reviews(client_token, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_reviews_client_hash_status
    ON reviews(client_token, diff_hash, status);

CREATE INDEX IF NOT EXISTS idx_reviews_status_created
    ON reviews(status, created_at ASC);

CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    agent TEXT NOT NULL,
    status TEXT NOT NULL,
    duration_s REAL,
    finding_count INTEGER,
    UNIQUE(review_id, agent)
);

CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    severity TEXT NOT NULL,
    confidence TEXT NOT NULL,
    cwe TEXT,
    file TEXT,
    line INTEGER,
    evidence TEXT,
    fix TEXT,
    sources TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL,
    rejection_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_findings_review_status
    ON findings(review_id, status, severity);

CREATE TABLE IF NOT EXISTS review_logs (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    ts TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_review_logs_review_ts
    ON review_logs(review_id, ts, id);
