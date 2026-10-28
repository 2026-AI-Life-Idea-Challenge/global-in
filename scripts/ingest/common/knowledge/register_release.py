"""
scripts/ingest/common/knowledge/register_release.py

knowledge_releases 테이블에 릴리즈 레코드를 등록합니다.
embed_chunks.py 실행 전에 반드시 먼저 실행하세요.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import psycopg2

DB_URL = os.environ.get(
    "DB_URL",
    "postgresql://global_in_app:outsiders4@localhost:5432/global_in"
)

RELEASE_DIR  = Path(__file__).resolve().parent.parent.parent.parent / \
    "data" / "processed" / "knowledge" / "20261028"
MANIFEST_PATH = RELEASE_DIR / "manifest.json"
CHUNKS_PATH   = RELEASE_DIR / "knowledge_chunks.json"
RELEASE_PATH  = RELEASE_DIR / "knowledge_release.json"

RELEASE_ID = "knowledge-v1-20261028"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def main():
    # sha256 계산할 파일 선택 (manifest > chunks > release 순)
    sha_source = None
    for candidate in [MANIFEST_PATH, CHUNKS_PATH, RELEASE_PATH]:
        if candidate.exists():
            sha_source = candidate
            break

    if sha_source is None:
        print("ERROR: sha256 계산할 파일이 없습니다.")
        sys.exit(1)

    manifest_sha256 = sha256_file(sha_source)
    print(f"manifest_sha256 source: {sha_source.name}")
    print(f"sha256: {manifest_sha256}")

    if MANIFEST_PATH.exists():
        with MANIFEST_PATH.open(encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        manifest = {}

    metadata = {
        "release_date": "2026-10-28",
        "source_version": "20261028",
        "description": manifest.get("description", "Knowledge release 2026-10-28"),
        "sha_source": sha_source.name,
    }

    conn = psycopg2.connect(DB_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT release_id FROM knowledge_releases WHERE release_id = %s",
                (RELEASE_ID,)
            )
            if cur.fetchone():
                print(f"Already exists: {RELEASE_ID}")
                return

        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO knowledge_releases (release_id, manifest_sha256, verified_at, metadata)
                    VALUES (%s, %s, NULL, %s)
                    ON CONFLICT (release_id) DO NOTHING
                """, (RELEASE_ID, manifest_sha256, json.dumps(metadata, ensure_ascii=False)))
                print(f"Inserted: {RELEASE_ID}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        conn.close()

    print("Done. 이제 embed_chunks.py 실행하세요.")


if __name__ == "__main__":
    main()