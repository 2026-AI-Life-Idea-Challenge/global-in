-- Migration: knowledge_chunk_embeddings
-- Stores Qwen3-Embedding-0.6B (1024-dim) vectors for knowledge_chunks.
-- embedding_approved must be True on the chunk before insertion (enforced by app layer).
-- Embedding execution requires explicit authorisation; do not run automatically.

CREATE TABLE IF NOT EXISTS knowledge_chunk_embeddings (
    embedding_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chunk_id         TEXT        NOT NULL,
    document_id      TEXT        NOT NULL,
    revision_id      TEXT        NOT NULL,
    release_id       TEXT        NOT NULL REFERENCES knowledge_releases(release_id),
    embedding_model  TEXT        NOT NULL,
    embedding        VECTOR(1024) NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (document_id, revision_id)
        REFERENCES knowledge_documents(document_id, revision_id),
    UNIQUE (chunk_id, embedding_model)
);

CREATE INDEX IF NOT EXISTS idx_kce_chunk_id
    ON knowledge_chunk_embeddings(chunk_id);

CREATE INDEX IF NOT EXISTS idx_kce_release_id
    ON knowledge_chunk_embeddings(release_id);

-- HNSW index for fast ANN similarity search (cosine)
CREATE INDEX IF NOT EXISTS idx_kce_embedding_hnsw
    ON knowledge_chunk_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
