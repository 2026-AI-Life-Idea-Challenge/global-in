"""
scripts/ingest/common/knowledge/embed_chunks.py

Embeds knowledge_chunks using Qwen3-Embedding-0.6B and inserts into
knowledge_chunk_embeddings table.

REQUIRES EXPLICIT AUTHORISATION before execution.
- Only chunks with embedding_approved=True in knowledge_chunks.json are embedded.
- Currently embedding_approved=False for all chunks → script exits safely.
- Set embedding_approved=True via authorised process before running.

Usage:
    python scripts/ingest/common/knowledge/embed_chunks.py [--dry-run]
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

# ── config ────────────────────────────────────────────────────────────────────
MODEL_NAME   = "Qwen/Qwen3-Embedding-0.6B"
EMBED_DIM    = 1024
BATCH_SIZE   = 32
RELEASE_DIR  = Path(__file__).resolve().parents[4] / "data" / "processed" / "knowledge" / "20261028"
CHUNKS_PATH  = RELEASE_DIR / "knowledge_chunks.json"
DB_URL       = os.environ.get("DATABASE_URL", "")

# ── safety gate ───────────────────────────────────────────────────────────────
AUTHORISED = False  # flip to True only after explicit approval


def load_approved_chunks(chunks_path: Path) -> list:
    with chunks_path.open(encoding="utf-8") as f:
        data = json.load(f)
    approved = [c for c in data["chunks"] if c.get("embedding_approved")]
    return approved, data.get("release_id")


def embed_batch(model, tokenizer, texts: list) -> list:
    """Returns list of 1024-dim float lists."""
    import torch
    inputs = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )
    with torch.no_grad():
        outputs = model(**inputs)
    # mean pooling
    attention_mask = inputs["attention_mask"]
    token_embeddings = outputs.last_hidden_state
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    embeddings = (token_embeddings * input_mask_expanded).sum(1) / input_mask_expanded.sum(1).clamp(min=1e-9)
    # L2 normalise for cosine similarity
    embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
    return embeddings.tolist()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Load model and chunks but do not write to DB")
    args = parser.parse_args()

    # ── authorisation gate ────────────────────────────────────────────────────
    if not AUTHORISED:
        print("[BLOCKED] Embedding execution requires explicit authorisation.")
        print("          Set AUTHORISED=True in this script after approval.")
        print("          Currently embedding_approved=False for all chunks — nothing to do.")
        sys.exit(0)

    if not DB_URL:
        print("[ERROR] DATABASE_URL not set.")
        sys.exit(1)

    approved_chunks, release_id = load_approved_chunks(CHUNKS_PATH)
    if not approved_chunks:
        print("[INFO] No chunks with embedding_approved=True. Nothing to embed.")
        sys.exit(0)

    print(f"Approved chunks: {len(approved_chunks)}  release_id: {release_id}")
    if args.dry_run:
        print("[DRY RUN] Would embed the above chunks. Exiting without DB writes.")
        sys.exit(0)

    # ── load model ────────────────────────────────────────────────────────────
    print(f"Loading model: {MODEL_NAME}")
    from transformers import AutoModel, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model     = AutoModel.from_pretrained(MODEL_NAME)
    model.eval()
    print("Model loaded.")

    # ── embed ─────────────────────────────────────────────────────────────────
    import psycopg2
    conn = psycopg2.connect(DB_URL)
    cur  = conn.cursor()

    inserted = skipped = 0
    for i in range(0, len(approved_chunks), BATCH_SIZE):
        batch = approved_chunks[i:i + BATCH_SIZE]
        texts = [c["body"] for c in batch]
        vecs  = embed_batch(model, tokenizer, texts)

        for chunk, vec in zip(batch, vecs):
            assert len(vec) == EMBED_DIM, f"Unexpected dim: {len(vec)}"
            try:
                cur.execute(
                    """
                    INSERT INTO knowledge_chunk_embeddings
                        (chunk_id, document_id, revision_id, release_id, embedding_model, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_id, embedding_model) DO NOTHING
                    """,
                    (
                        chunk["chunk_id"],
                        chunk["document_id"],
                        chunk["revision_id"],
                        chunk["release_id"],
                        MODEL_NAME,
                        vec,
                    ),
                )
                inserted += cur.rowcount
                skipped  += 1 - cur.rowcount
            except Exception as e:
                conn.rollback()
                print(f"[ERROR] {chunk['chunk_id']}: {e}")
                continue

        conn.commit()
        print(f"  batch {i // BATCH_SIZE + 1}: {len(batch)} chunks processed")

    cur.close()
    conn.close()
    print(f"Done. inserted={inserted}  skipped(already exist)={skipped}")


if __name__ == "__main__":
    main()
