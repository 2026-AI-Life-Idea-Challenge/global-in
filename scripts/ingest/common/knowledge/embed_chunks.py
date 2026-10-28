"""
scripts/ingest/common/knowledge/embed_chunks.py

Embeds knowledge_chunks using Qwen3-Embedding-0.6B and inserts into
knowledge_chunk_embeddings table.

AUTHORISED=True — approved 2026-10-28.
embedding_approved=True set on all 585 chunks.
"""

import argparse
import json
import os
import sys
from pathlib import Path

MODEL_NAME  = "Qwen/Qwen3-Embedding-0.6B"
EMBED_DIM   = 1024
BATCH_SIZE  = 32
RELEASE_DIR = Path(__file__).resolve().parents[4] / "data" / "processed" / "knowledge" / "20261028"
CHUNKS_PATH = RELEASE_DIR / "knowledge_chunks.json"
DB_URL      = os.environ.get("DATABASE_URL", "postgresql://global_in_app:outsiders4@localhost:5432/global_in")

AUTHORISED  = True  # approved 2026-10-28


def load_approved_chunks(chunks_path):
    with chunks_path.open(encoding="utf-8") as f:
        data = json.load(f)
    approved = [c for c in data["chunks"] if c.get("embedding_approved")]
    return approved, data.get("release_id")


def embed_batch(model, tokenizer, texts, device):
    import torch
    inputs = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    attention_mask = inputs["attention_mask"]
    token_embeddings = outputs.last_hidden_state
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    embeddings = (token_embeddings * input_mask_expanded).sum(1) / input_mask_expanded.sum(1).clamp(min=1e-9)
    embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
    return embeddings.cpu().tolist()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not AUTHORISED:
        print("[BLOCKED] Set AUTHORISED=True after explicit approval.")
        sys.exit(0)

    approved_chunks, release_id = load_approved_chunks(CHUNKS_PATH)
    if not approved_chunks:
        print("[INFO] No approved chunks. Nothing to embed.")
        sys.exit(0)

    print(f"Approved chunks: {len(approved_chunks)}  release_id: {release_id}")

    if args.dry_run:
        print("[DRY RUN] Exiting without DB writes.")
        sys.exit(0)

    import torch
    from transformers import AutoModel, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    print(f"Loading model: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME).to(device)
    model.eval()
    print("Model loaded.")

    import psycopg2
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    inserted = skipped = errors = 0
    total_batches = (len(approved_chunks) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(approved_chunks), BATCH_SIZE):
        batch = approved_chunks[i:i + BATCH_SIZE]
        texts = [c["body"] for c in batch]
        vecs  = embed_batch(model, tokenizer, texts, device)

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
                if cur.rowcount:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                conn.rollback()
                print(f"[ERROR] {chunk['chunk_id']}: {e}")
                errors += 1
                continue

        conn.commit()
        batch_num = i // BATCH_SIZE + 1
        print(f"  [{batch_num}/{total_batches}] {min(i+BATCH_SIZE, len(approved_chunks))}/{len(approved_chunks)} chunks done")

    cur.close()
    conn.close()
    print(f"\nDone. inserted={inserted}  skipped={skipped}  errors={errors}")


if __name__ == "__main__":
    main()
