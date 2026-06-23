-- Database migration to create the embedding cache table
CREATE TABLE IF NOT EXISTS embedding_cache (
    chunk_hash TEXT PRIMARY KEY,
    embedding TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
