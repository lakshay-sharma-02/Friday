CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    importance REAL DEFAULT 0.0,
    created_at TEXT NOT NULL,
    last_accessed TEXT NOT NULL,
    reinforcement_count INTEGER DEFAULT 0,
    project_tag TEXT,
    superseded_by TEXT,
    source TEXT
);

CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance);

CREATE TABLE IF NOT EXISTS history (
    id TEXT PRIMARY KEY,
    intent_id TEXT NOT NULL,
    run_status TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    raw_data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS embedding_index (
    id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_version TEXT NOT NULL,
    embedding_vector BLOB NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(memory_id) REFERENCES memories(id) ON DELETE CASCADE
);

