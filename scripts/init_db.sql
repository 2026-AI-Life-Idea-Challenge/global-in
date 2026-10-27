
BEGIN;

CREATE TABLE IF NOT EXISTS programs (
    program_id TEXT PRIMARY KEY,
    country TEXT NOT NULL
        CHECK (country IN ('japan', 'australia', 'usa', 'germany', 'canada')),
    name TEXT NOT NULL,
    category TEXT,
    route_id TEXT,
    visa_subclass TEXT,
    stream TEXT,
    source_program_id TEXT,
    source_file TEXT,
    review_status TEXT NOT NULL DEFAULT 'needs_review',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS support_programs (
    support_program_id TEXT PRIMARY KEY,
    country TEXT NOT NULL
        CHECK (country IN ('japan', 'australia', 'usa', 'germany', 'canada')),
    name TEXT NOT NULL,
    provider TEXT,
    source_file TEXT,
    review_status TEXT NOT NULL DEFAULT 'needs_review',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL REFERENCES programs(program_id),
    country TEXT NOT NULL
        CHECK (country IN ('japan', 'australia', 'usa', 'germany', 'canada')),
    source_evidence_id TEXT,
    source_id TEXT,
    source_url TEXT,
    source_file TEXT,
    source_sha256 TEXT,
    exact_quote TEXT,
    source_location TEXT,
    review_status TEXT NOT NULL DEFAULT 'needs_review',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS policy_candidates (
    policy_id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL REFERENCES programs(program_id),
    country TEXT NOT NULL
        CHECK (country IN ('japan', 'australia', 'usa', 'germany', 'canada', 'multi_country')),
    topic TEXT,
    source_evidence_ids TEXT[] NOT NULL DEFAULT '{}',
    policy_text TEXT,
    review_status TEXT NOT NULL DEFAULT 'needs_review',
    legal_validation_approved BOOLEAN NOT NULL DEFAULT FALSE,
    approved_for_eligibility_decision BOOLEAN NOT NULL DEFAULT FALSE,
    approved_for_embedding BOOLEAN NOT NULL DEFAULT FALSE,
    approved_for_user_answers BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evidence_embeddings (
    embedding_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id) ON DELETE CASCADE,
    embedding_model TEXT NOT NULL,
    embedding VECTOR NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (evidence_id, embedding_model)
);

CREATE INDEX IF NOT EXISTS idx_programs_country
    ON programs(country);

CREATE INDEX IF NOT EXISTS idx_support_programs_country
    ON support_programs(country);

CREATE INDEX IF NOT EXISTS idx_evidence_program
    ON evidence(program_id);

CREATE INDEX IF NOT EXISTS idx_policy_candidates_program
    ON policy_candidates(program_id);

COMMIT;