CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    intent_text TEXT NOT NULL,
    intent_kind TEXT NOT NULL,
    plan_json TEXT,
    execution_log_json TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    access_count INTEGER DEFAULT 0,
    last_accessed_at TEXT,
    tier TEXT DEFAULT 'HOT'
);

CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'lesson',
    source_run_id TEXT,
    created_at TEXT NOT NULL,
    access_count INTEGER DEFAULT 0,
    last_accessed_at TEXT,
    tier TEXT DEFAULT 'HOT',
    FOREIGN KEY (source_run_id) REFERENCES runs(id)
);

CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at);
CREATE INDEX IF NOT EXISTS idx_runs_tier ON runs(tier);
CREATE INDEX IF NOT EXISTS idx_notes_tier ON notes(tier);
CREATE INDEX IF NOT EXISTS idx_notes_source ON notes(source);
