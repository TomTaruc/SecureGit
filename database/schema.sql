-- =============================================================================
-- SecureGit Database Schema
-- Database: securegit_db
-- PostgreSQL 15+
-- All timestamps: TIMESTAMPTZ
-- All PKs: SERIAL PRIMARY KEY
-- =============================================================================

-- Create the database (run as superuser before this script)
-- CREATE DATABASE securegit_db;
-- \c securegit_db

-- ---------------------------------------------------------------------------
-- 1. USERS
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id        SERIAL PRIMARY KEY,
    username       VARCHAR(50)  UNIQUE NOT NULL,
    email          VARCHAR(255) UNIQUE NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,
    role           VARCHAR(20)  NOT NULL DEFAULT 'dev'
                       CHECK (role IN ('admin', 'dev', 'read')),
    is_suspended   BOOLEAN      NOT NULL DEFAULT FALSE,
    fingerprint    VARCHAR(255),
    last_login     TIMESTAMPTZ,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email    ON users(email);

-- ---------------------------------------------------------------------------
-- 2. SSH_KEYS
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ssh_keys (
    key_id       SERIAL PRIMARY KEY,
    user_id      INT          NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title        VARCHAR(100) NOT NULL,
    key_type     VARCHAR(20)  NOT NULL
                     CHECK (key_type IN ('ssh-ed25519', 'ssh-rsa', 'ecdsa-sha2-nistp256')),
    public_key   TEXT         NOT NULL UNIQUE,
    fingerprint  VARCHAR(255) NOT NULL UNIQUE,
    added_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ssh_keys_user_id ON ssh_keys(user_id);

-- ---------------------------------------------------------------------------
-- 3. PROJECTS
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    project_id     SERIAL PRIMARY KEY,
    owner_user_id  INT          NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    project_name   VARCHAR(100) NOT NULL,
    description    TEXT,
    visibility     VARCHAR(10)  NOT NULL DEFAULT 'private'
                       CHECK (visibility IN ('private', 'internal')),
    default_branch VARCHAR(100) NOT NULL DEFAULT 'main',
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE(owner_user_id, project_name)
);

CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_user_id);

-- ---------------------------------------------------------------------------
-- 4. REPOSITORIES
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS repositories (
    repo_id          SERIAL PRIMARY KEY,
    project_id       INT          NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    repo_project_id  INT          NOT NULL REFERENCES projects(project_id),
    repo_path        VARCHAR(255) NOT NULL UNIQUE,
    clone_url        VARCHAR(255) NOT NULL,
    is_initialized   BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_repositories_project ON repositories(project_id);

-- ---------------------------------------------------------------------------
-- 5. CHROOT_JAILS
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chroot_jails (
    jail_id      SERIAL PRIMARY KEY,
    project_id   INT          NOT NULL REFERENCES projects(project_id)  ON DELETE CASCADE,
    user_id      INT          NOT NULL REFERENCES users(user_id)         ON DELETE CASCADE,
    jail_path    VARCHAR(255) NOT NULL UNIQUE,
    fs_jail_user VARCHAR(50)  NOT NULL,
    status       VARCHAR(20)  NOT NULL DEFAULT 'active'
                     CHECK (status IN ('active', 'suspended')),
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 6. BRANCHES
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS branches (
    branch_id   SERIAL PRIMARY KEY,
    repo_id     INT          NOT NULL REFERENCES repositories(repo_id) ON DELETE CASCADE,
    branch_name VARCHAR(255) NOT NULL,
    is_default  BOOLEAN      NOT NULL DEFAULT FALSE,
    is_locked   BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE(repo_id, branch_name)
);

CREATE INDEX IF NOT EXISTS idx_branches_repo ON branches(repo_id);

-- ---------------------------------------------------------------------------
-- 7. COMMITS
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS commits (
    commit_id            SERIAL PRIMARY KEY,
    branch_id            INT      NOT NULL REFERENCES branches(branch_id)  ON DELETE CASCADE,
    author_id            INT      NOT NULL REFERENCES users(user_id),
    commit_hash          CHAR(40) NOT NULL UNIQUE,
    short_hash           CHAR(7)  NOT NULL,
    message              TEXT     NOT NULL,
    committed_at         TIMESTAMPTZ NOT NULL,
    parent_hash          CHAR(40),
    fs_commit_author_id  INT REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_commits_branch ON commits(branch_id);
CREATE INDEX IF NOT EXISTS idx_commits_author ON commits(author_id);
CREATE INDEX IF NOT EXISTS idx_commits_hash   ON commits(commit_hash);
CREATE INDEX IF NOT EXISTS idx_commits_date   ON commits(committed_at DESC);

-- ---------------------------------------------------------------------------
-- 8. FILES
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS files (
    file_id    SERIAL PRIMARY KEY,
    repo_id    INT           NOT NULL REFERENCES repositories(repo_id) ON DELETE CASCADE,
    file_path  VARCHAR(4096) NOT NULL,
    file_name  VARCHAR(255)  NOT NULL,
    created_at TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE(repo_id, file_path)
);

CREATE INDEX IF NOT EXISTS idx_files_repo ON files(repo_id);

-- ---------------------------------------------------------------------------
-- 9. COMMIT_FILES (junction)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS commit_files (
    cf_id         SERIAL PRIMARY KEY,
    commit_id     INT         NOT NULL REFERENCES commits(commit_id)  ON DELETE CASCADE,
    file_id       INT         NOT NULL REFERENCES files(file_id)      ON DELETE CASCADE,
    change_type   VARCHAR(10) NOT NULL
                      CHECK (change_type IN ('added', 'modified', 'deleted', 'renamed')),
    lines_added   INT         NOT NULL DEFAULT 0,
    lines_deleted INT         NOT NULL DEFAULT 0,
    diff_content  TEXT,
    UNIQUE(commit_id, file_id)
);

CREATE INDEX IF NOT EXISTS idx_commit_files_commit ON commit_files(commit_id);

-- ---------------------------------------------------------------------------
-- 10. COLLABORATORS (enhanced with RBAC JSONB permissions)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS collaborators (
    collab_id             SERIAL PRIMARY KEY,
    project_id            INT         NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    user_id               INT         NOT NULL REFERENCES users(user_id)       ON DELETE CASCADE,
    -- Legacy simple permission kept for backward compat (computed from JSONB)
    permission            VARCHAR(20) NOT NULL DEFAULT 'read'
                              CHECK (permission IN ('read', 'write', 'admin')),
    -- RBAC: granular permission flags
    permissions           JSONB       NOT NULL DEFAULT '{
        "read": true,
        "push": false,
        "create_branch": false,
        "delete_branch": false,
        "manage_collaborators": false,
        "manage_settings": false,
        "admin": false
    }'::jsonb,
    granted_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fs_collab_project_id  INT REFERENCES projects(project_id),
    fs_collab_user_id     INT REFERENCES users(user_id),
    UNIQUE(project_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_collaborators_project ON collaborators(project_id);
CREATE INDEX IF NOT EXISTS idx_collaborators_user    ON collaborators(user_id);

-- ---------------------------------------------------------------------------
-- 11. AUDIT_LOG
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    log_id      SERIAL PRIMARY KEY,
    actor_id    INT          NOT NULL REFERENCES users(user_id),
    action      VARCHAR(100) NOT NULL,
    target_id   INT,
    target_type VARCHAR(50),
    detail      TEXT,
    ip_address  VARCHAR(45),
    occurred_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_time  ON audit_log(occurred_at DESC);

-- PostgreSQL NOTIFY trigger for real-time audit streaming
CREATE OR REPLACE FUNCTION notify_audit_insert()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('audit_log_insert', row_to_json(NEW)::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_notify
    AFTER INSERT ON audit_log
    FOR EACH ROW EXECUTE FUNCTION notify_audit_insert();

-- =============================================================================
-- ENHANCEMENT TABLES
-- =============================================================================

-- ---------------------------------------------------------------------------
-- E1. BRANCH_PROTECTION_RULES
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS branch_protection_rules (
    rule_id              SERIAL PRIMARY KEY,
    repo_id              INT          NOT NULL REFERENCES repositories(repo_id) ON DELETE CASCADE,
    branch_pattern       VARCHAR(255) NOT NULL,   -- e.g. 'main', 'release/*'
    disable_force_push   BOOLEAN      NOT NULL DEFAULT TRUE,
    disable_deletion     BOOLEAN      NOT NULL DEFAULT TRUE,
    restrict_push        BOOLEAN      NOT NULL DEFAULT FALSE,
    allowed_push_roles   JSONB        NOT NULL DEFAULT '["admin"]'::jsonb,
    require_admin_for_push BOOLEAN    NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE(repo_id, branch_pattern)
);

CREATE INDEX IF NOT EXISTS idx_branch_protection_repo ON branch_protection_rules(repo_id);

-- ---------------------------------------------------------------------------
-- E2. REPO_TOKENS (machine/CI token authentication)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS repo_tokens (
    token_id    SERIAL PRIMARY KEY,
    repo_id     INT          NOT NULL REFERENCES repositories(repo_id) ON DELETE CASCADE,
    user_id     INT          NOT NULL REFERENCES users(user_id)         ON DELETE CASCADE,
    name        VARCHAR(100) NOT NULL,
    token_hash  VARCHAR(255) NOT NULL UNIQUE,     -- bcrypt hashed token
    scopes      JSONB        NOT NULL DEFAULT '["read"]'::jsonb,
    expires_at  TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_repo_tokens_repo ON repo_tokens(repo_id);
CREATE INDEX IF NOT EXISTS idx_repo_tokens_user ON repo_tokens(user_id);

-- ---------------------------------------------------------------------------
-- E3. BACKUP_JOBS
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS backup_jobs (
    job_id        SERIAL PRIMARY KEY,
    triggered_by  INT          REFERENCES users(user_id),  -- NULL = scheduled/cron
    status        VARCHAR(20)  NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    backup_type   VARCHAR(20)  NOT NULL DEFAULT 'full'
                      CHECK (backup_type IN ('full', 'repos_only', 'db_only')),
    destination   VARCHAR(255) NOT NULL,
    archive_path  VARCHAR(255),
    size_bytes    BIGINT,
    error_message TEXT,
    started_at    TIMESTAMPTZ,
    completed_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backup_jobs_status ON backup_jobs(status);
CREATE INDEX IF NOT EXISTS idx_backup_jobs_date   ON backup_jobs(created_at DESC);

-- ---------------------------------------------------------------------------
-- E4. WEBHOOK_ENDPOINTS (internal webhooks only)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS webhook_endpoints (
    webhook_id   SERIAL PRIMARY KEY,
    project_id   INT          NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    name         VARCHAR(100) NOT NULL,
    target_url   VARCHAR(512) NOT NULL,          -- must be localhost/LAN only (enforced in app)
    events       JSONB        NOT NULL DEFAULT '["push"]'::jsonb,
    secret_hash  VARCHAR(255),                   -- HMAC secret for signature
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    last_delivery_at   TIMESTAMPTZ,
    last_delivery_status INT,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_webhooks_project ON webhook_endpoints(project_id);

-- ---------------------------------------------------------------------------
-- E5. SERVER_CONFIG (admin-editable instance settings)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS server_config (
    config_id   SERIAL PRIMARY KEY,
    key         VARCHAR(100) NOT NULL UNIQUE,
    value       TEXT         NOT NULL,
    description TEXT,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_by  INT          REFERENCES users(user_id)
);

-- Default config values
INSERT INTO server_config (key, value, description) VALUES
    ('instance_title',         'SecureGit',    'Display name of this instance'),
    ('max_repo_size_mb',       '5120',          'Maximum repository size in MB'),
    ('signup_enabled',         'false',         'Allow self-registration'),
    ('default_branch_name',    'main',          'Default branch for new repositories'),
    ('max_ssh_keys_per_user',  '10',            'Maximum SSH keys per user account'),
    ('backup_dest_path',       '/mnt/backup',   'Default backup destination directory'),
    ('backup_schedule_cron',   '0 2 * * *',     'Cron expression for automated backups'),
    ('session_timeout_minutes','60',            'Web session timeout in minutes')
ON CONFLICT (key) DO NOTHING;

-- =============================================================================
-- POSTGRESQL SECURITY — Application Role
-- =============================================================================
-- Run as superuser after schema creation:
--
-- CREATE ROLE securegit_app WITH LOGIN PASSWORD 'CHANGE_ME_STRONG_PASSWORD';
-- GRANT CONNECT ON DATABASE securegit_db TO securegit_app;
-- GRANT USAGE ON SCHEMA public TO securegit_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO securegit_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO securegit_app;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public
--     GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO securegit_app;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public
--     GRANT USAGE, SELECT ON SEQUENCES TO securegit_app;
