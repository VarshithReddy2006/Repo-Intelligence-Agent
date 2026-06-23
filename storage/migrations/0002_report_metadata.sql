-- Database migration to add repository report persistence table
CREATE TABLE IF NOT EXISTS repo_reports (
    repo_name TEXT,
    overall_score REAL,
    grade TEXT,
    architecture_score REAL,
    api_score REAL,
    hygiene_score REAL,
    churn_score REAL,
    readability_score REAL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    report_data TEXT, -- JSON serialization of ReportDataModel
    PRIMARY KEY(repo_name, generated_at),
    FOREIGN KEY(repo_name) REFERENCES repositories(repo_name) ON DELETE CASCADE
);
