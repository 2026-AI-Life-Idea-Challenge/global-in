"""
scripts/ingest/common/knowledge/load_chunks.py

knowledge_chunks.json → knowledge_chunks 테이블 INSERT
"""
import json
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras

DB_URL = os.environ.get(
    "DB_URL",
    "postgresql://global_in_app:outsiders4@localhost:5432/global_in"
)

CHUNKS_PATH = (
    Path(__file__).resolve().parents[4]
    / "data" / "processed" / "knowledge" / "20261028" / "knowledge_chunks.json"
)


def main():
    print(f"Reading: {CHUNKS_PATH}")
    with CHUNKS_PATH.open(encoding="utf-8") as f:
        db = json.load(f)

    chunks = db["chunks"]
    release_id = db["release_id"]
    print(f"Chunks: {len(chunks)}  release_id: {release_id}")

    conn = psycopg2.connect(DB_URL)
    try:
        inserted = 0
        skipped = 0
        errors = 0

        with conn:
            with conn.cursor() as cur:
                for c in chunks:
                    try:
                        cur.execute("""
                            INSERT INTO knowledge_chunks
                                (chunk_id, document_id, revision_id, ordinal, body,
                                 content_sha256, metadata, active, embedding_approved, release_id)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (chunk_id) DO NOTHING
                        """, (
                            c["chunk_id"],
                            c["document_id"],
                            c["revision_id"],
                            c["ordinal"],
                            c["body"],
                            c["content_sha256"],
                            json.dumps(c["metadata"], ensure_ascii=False),
                            c["active"],
                            c["embedding_approved"],
                            c["release_id"],
                        ))
                        if cur.rowcount == 1:
                            inserted += 1
                        else:
                            skipped += 1
                    except Exception as e:
                        print(f"  오류 [{c['chunk_id']}]: {e}")
                        errors += 1
                        conn.rollback()

        print(f"Done. inserted={inserted}  skipped={skipped}  errors={errors}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()