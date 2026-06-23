-- Initial schema setup for repository relational storage
CREATE TABLE IF NOT EXISTS repositories (
    repo_name TEXT PRIMARY KEY,
    owner TEXT,
    name TEXT,
    cloned_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS repo_analyses (
    repo_name TEXT PRIMARY KEY,
    tech_stack TEXT, -- JSON array
    dependencies TEXT, -- JSON array
    analysis_data TEXT, -- JSON payload
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(repo_name) REFERENCES repositories(repo_name) ON DELETE CASCADE
);
