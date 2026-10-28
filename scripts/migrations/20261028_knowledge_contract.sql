-- Additive migration. Original evidence, policies, and their release gates stay intact.
CREATE TABLE IF NOT EXISTS knowledge_releases (
 release_id TEXT PRIMARY KEY, manifest_sha256 TEXT NOT NULL,
 verified_at DATE NOT NULL, metadata JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS support_program_profiles (
 support_program_id TEXT PRIMARY KEY REFERENCES support_programs(support_program_id),
 publisher_countries TEXT[] NOT NULL, destination_countries TEXT[] NOT NULL,
 korean_applicability TEXT NOT NULL, availability TEXT NOT NULL CHECK(availability IN ('OPEN','CLOSED','UPCOMING','UNKNOWN')),
 source_verified_at DATE NOT NULL, profile JSONB NOT NULL,
 release_id TEXT NOT NULL REFERENCES knowledge_releases(release_id)
);
CREATE TABLE IF NOT EXISTS program_profiles (
 program_id TEXT PRIMARY KEY REFERENCES programs(program_id),
 publisher_countries TEXT[] NOT NULL, destination_countries TEXT[] NOT NULL,
 profile JSONB NOT NULL, release_id TEXT NOT NULL REFERENCES knowledge_releases(release_id)
);
CREATE TABLE IF NOT EXISTS program_support_links (
 program_id TEXT NOT NULL REFERENCES programs(program_id),
 support_program_id TEXT NOT NULL REFERENCES support_programs(support_program_id),
 relationship TEXT NOT NULL, eligibility_implied BOOLEAN NOT NULL DEFAULT FALSE CHECK(NOT eligibility_implied),
 conditions JSONB NOT NULL, source_urls JSONB NOT NULL, release_id TEXT NOT NULL REFERENCES knowledge_releases(release_id),
 PRIMARY KEY(program_id,support_program_id)
);
CREATE TABLE IF NOT EXISTS knowledge_documents (
 document_id TEXT NOT NULL, revision_id TEXT NOT NULL,
 content_sha256 TEXT NOT NULL, knowledge_kind TEXT NOT NULL,
 title TEXT NOT NULL, body TEXT NOT NULL, metadata JSONB NOT NULL,
 active BOOLEAN NOT NULL, release_id TEXT NOT NULL REFERENCES knowledge_releases(release_id),
 PRIMARY KEY(document_id,revision_id)
);
CREATE TABLE IF NOT EXISTS knowledge_document_targets (
 document_id TEXT NOT NULL, revision_id TEXT NOT NULL,
 target_type TEXT NOT NULL CHECK(target_type IN ('PROGRAM','SUPPORT_PROGRAM')), target_id TEXT NOT NULL,
 PRIMARY KEY(document_id,revision_id,target_type,target_id),
 FOREIGN KEY(document_id,revision_id) REFERENCES knowledge_documents(document_id,revision_id)
);
CREATE TABLE IF NOT EXISTS eligibility_requirements (
 requirement_id TEXT PRIMARY KEY, target_type TEXT NOT NULL, target_id TEXT NOT NULL,
 judgeability TEXT NOT NULL CHECK(judgeability IN ('rule_based','manual_check','conditional')),
 definition JSONB NOT NULL, release_id TEXT NOT NULL REFERENCES knowledge_releases(release_id)
);
CREATE TABLE IF NOT EXISTS eligibility_rule_sets (
 rule_set_id TEXT PRIMARY KEY, target_type TEXT NOT NULL CHECK(target_type IN ('PROGRAM','SUPPORT_PROGRAM')),
 target_id TEXT NOT NULL, coverage_complete BOOLEAN NOT NULL DEFAULT FALSE,
 definition JSONB NOT NULL, release_id TEXT NOT NULL REFERENCES knowledge_releases(release_id),
 UNIQUE(target_type,target_id)
);
CREATE TABLE IF NOT EXISTS preparation_items (
 item_id TEXT PRIMARY KEY, target_type TEXT NOT NULL, target_id TEXT NOT NULL,
 stage TEXT NOT NULL, item_kind TEXT NOT NULL,
 definition JSONB NOT NULL, release_id TEXT NOT NULL REFERENCES knowledge_releases(release_id)
);
CREATE TABLE IF NOT EXISTS knowledge_chunks (
 chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, revision_id TEXT NOT NULL,
 ordinal INTEGER NOT NULL, body TEXT NOT NULL CHECK(length(body)>0), content_sha256 TEXT NOT NULL,
 metadata JSONB NOT NULL, active BOOLEAN NOT NULL,
 embedding_approved BOOLEAN NOT NULL DEFAULT FALSE,
 release_id TEXT NOT NULL REFERENCES knowledge_releases(release_id),
 FOREIGN KEY(document_id,revision_id) REFERENCES knowledge_documents(document_id,revision_id),
 UNIQUE(document_id,revision_id,ordinal)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_targets ON knowledge_document_targets(target_type,target_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_active ON knowledge_chunks(active);
CREATE INDEX IF NOT EXISTS idx_knowledge_metadata ON knowledge_documents USING gin(metadata);
CREATE OR REPLACE VIEW knowledge_documents_current AS SELECT * FROM knowledge_documents WHERE active;
CREATE OR REPLACE VIEW knowledge_chunks_current AS SELECT * FROM knowledge_chunks WHERE active;
