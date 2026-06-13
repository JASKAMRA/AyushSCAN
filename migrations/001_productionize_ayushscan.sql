PRAGMA foreign_keys = ON;

ALTER TABLE users ADD COLUMN preferred_language TEXT DEFAULT 'english';
ALTER TABLE users ADD COLUMN created_at DATETIME;

ALTER TABLE scans ADD COLUMN report TEXT DEFAULT '{}';
ALTER TABLE scans ADD COLUMN savings REAL DEFAULT 0;

ALTER TABLE otp_tokens ADD COLUMN purpose TEXT DEFAULT 'forgot_password';
ALTER TABLE otp_tokens ADD COLUMN used INTEGER DEFAULT 0;

CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    language TEXT DEFAULT 'english',
    mode TEXT DEFAULT 'gemini',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scans_user_timestamp ON scans(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_chat_user_timestamp ON chat_history(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_otp_email_purpose ON otp_tokens(email, purpose, used);
