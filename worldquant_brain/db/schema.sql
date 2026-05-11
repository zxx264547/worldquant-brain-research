-- WorldQuant BRAIN Alpha Research Database Schema
-- SQLite with WAL mode for concurrent access

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS alphas (
    id TEXT PRIMARY KEY,                 -- alpha_id from BRAIN API
    expression TEXT NOT NULL,
    expression_hash TEXT UNIQUE NOT NULL, -- SHA256 for dedup
    sharpe REAL DEFAULT 0,
    fitness REAL DEFAULT 0,
    ppc REAL DEFAULT 0,
    margin REAL DEFAULT 0,
    turnover REAL DEFAULT 0,
    settings_json TEXT DEFAULT '{}',     -- backtest settings used
    name TEXT,                           -- human-readable name
    combo_type TEXT,                     -- mul/add/rank/base
    base_alpha TEXT,                     -- parent alpha name
    tech_signal TEXT,                    -- technical signal name
    weight REAL,                         -- combination weight
    status TEXT DEFAULT 'done',          -- pending/running/done/error
    error_message TEXT,
    is_submittable INTEGER DEFAULT 0,    -- boolean
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy TEXT NOT NULL,
    expression TEXT NOT NULL,
    expression_hash TEXT NOT NULL,
    settings_json TEXT DEFAULT '{}',
    status TEXT DEFAULT 'queued',        -- queued/running/done/failed
    priority INTEGER DEFAULT 0,
    worker_id TEXT,
    retries INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    alpha_id TEXT,                       -- result alpha_id
    sharpe REAL,
    error_message TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS workers (
    id TEXT PRIMARY KEY,
    status TEXT DEFAULT 'idle',          -- idle/busy/dead
    current_task_id INTEGER,
    last_heartbeat TEXT DEFAULT (datetime('now')),
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    strategy TEXT NOT NULL,
    config_json TEXT DEFAULT '{}',
    status TEXT DEFAULT 'running',       -- running/done/aborted
    total_tasks INTEGER DEFAULT 0,
    completed_tasks INTEGER DEFAULT 0,
    best_sharpe REAL DEFAULT 0,
    started_at TEXT DEFAULT (datetime('now')),
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,                 -- dataset_id from BRAIN API
    name TEXT,
    field_count INTEGER DEFAULT 0,
    fields_json TEXT DEFAULT '[]',
    last_fetched TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS valid_fields (
    field_name TEXT PRIMARY KEY,
    dataset_id TEXT,
    data_type TEXT,
    first_seen TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_alphas_sharpe ON alphas(sharpe DESC);
CREATE INDEX IF NOT EXISTS idx_alphas_fitness ON alphas(fitness DESC);
CREATE INDEX IF NOT EXISTS idx_alphas_submittable ON alphas(is_submittable) WHERE is_submittable = 1;
CREATE INDEX IF NOT EXISTS idx_alphas_combo ON alphas(combo_type);
CREATE INDEX IF NOT EXISTS idx_alphas_created ON alphas(created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(status, priority DESC);
CREATE INDEX IF NOT EXISTS idx_workers_status ON workers(status);
CREATE INDEX IF NOT EXISTS idx_experiments_active ON experiments(status) WHERE status = 'running';
