-- ============================================================
-- DataLens Production Fix - Missing Tables
-- Run this in Neon SQL Editor: https://console.neon.tech
-- Project: Densho → SQL Editor → Paste & Run
-- ============================================================

-- 1. Create email_verifications table
CREATE TABLE IF NOT EXISTS email_verifications (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    otp_hash VARCHAR(255) NOT NULL,
    temp_password_hash VARCHAR(255),
    temp_full_name VARCHAR(255),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    attempts INTEGER DEFAULT 0,
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster email lookups during OTP verification
CREATE INDEX IF NOT EXISTS idx_email_verifications_email
ON email_verifications(email);

-- Index for cleanup queries on expired records
CREATE INDEX IF NOT EXISTS idx_email_verifications_expires
ON email_verifications(expires_at);


-- 2. Create refresh_tokens table
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    revoked_at TIMESTAMP WITH TIME ZONE
);

-- Index for user token lookups
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id
ON refresh_tokens(user_id);

-- Index for token validation
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash
ON refresh_tokens(token_hash);

-- Index for cleanup of expired tokens
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires
ON refresh_tokens(expires_at);


-- 3. Verification query - run this to confirm tables exist
SELECT table_name,
       (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
AND table_name IN ('email_verifications', 'refresh_tokens', 'users')
ORDER BY table_name;
