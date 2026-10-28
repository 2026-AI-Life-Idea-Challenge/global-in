"""
scripts/ingest/common/knowledge/build_chunks.py

Produces knowledge_chunks.json from knowledge_release.json.
Strategy:
  - Documents <= SPLIT_THRESHOLD chars → single chunk (ordinal 0)
  - Documents >  SPLIT_THRESHOLD chars → split on double-newline paragraphs,
    then merge tiny paragraphs (<MIN_PARA) with the next one to avoid
    near-empty chunks. Each resulting segment becomes one chunk.

Output schema matches knowledge_chunks table:
  chunk_id        TEXT  "{document_id}::{revision_id}::chunk{ordinal}"
  document_id     TEXT
  revision_id     TEXT
  ordinal         INT
  body            TEXT  (non-empty, guaranteed by filter)
  content_sha256  TEXT  sha256(body.encode())
  metadata        dict  {knowledge_kind, title, topics, destination_countries,
                         targets, source_char_len, split_strategy}
  active          bool  (mirrors parent document)
  embedding_approved bool  False always -- must be set by authorised process
  release_id      TEXT
"""

import hashlib
import json
import re
import sys
from pathlib import Path

# -- config -------------------------------------------------------------------
SPLIT_THRESHOLD = 2000   # chars; docs above this are paragraph-split
MIN_PARA        = 80     # merge paragraphs shorter than this with next

# -- paths --------------------------------------------------------------------
REPO_ROOT    = Path(__file__).resolve().parents[4]
RELEASE_DIR  = REPO_ROOT / "data" / "processed" / "knowledge" / "20261028"
INPUT_PATH   = RELEASE_DIR / "knowledge_release.json"
OUTPUT_PATH  = RELEASE_DIR / "knowledge_chunks.json"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_paragraphs(text: str) -> list:
    """Split on blank lines; merge tiny paragraphs with the next."""
    raw = re.split(r"\n{2,}", text.strip())
    merged = []
    buf = ""
    for para in raw:
        para = para.strip()
        if not para:
            continue
        if buf:
            buf = buf + "\n\n" + para
        else:
            buf = para
        if len(buf) >= MIN_PARA:
            merged.append(buf)
            buf = ""
    if buf:
        if merged:
            merged[-1] = merged[-1] + "\n\n" + buf
        else:
            merged.append(buf)
    return merged if merged else [text.strip()]


def chunk_document(doc, release_id):
    doc_id   = doc["document_id"]
    rev_id   = doc["revision_id"]
    text     = (doc.get("text") or "").strip()
    active   = doc.get("active", True)

    base_meta = {
        "knowledge_kind":        doc.get("knowledge_kind"),
        "title":                 doc.get("title"),
        "topics":                doc.get("topics", []),
        "destination_countries": doc.get("destination_countries", []),
        "targets":               [t.get("target_id") for t in doc.get("targets", [])],
        "source_char_len":       len(text),
    }

    if not text:
        return []

    if len(text) <= SPLIT_THRESHOLD:
        segments       = [text]
        split_strategy = "single"
    else:
        segments       = split_paragraphs(text)
        split_strategy = "paragraph"

    chunks = []
    for ordinal, segment in enumerate(segments):
        segment = segment.strip()
        if not segment:
            continue
        chunk_id = f"{doc_id}::{rev_id}::chunk{ordinal}"
        meta = {**base_meta, "split_strategy": split_strategy}
        chunks.append({
            "chunk_id":           chunk_id,
            "document_id":        doc_id,
            "revision_id":        rev_id,
            "ordinal":            ordinal,
            "body":               segment,
            "content_sha256":     sha256(segment),
            "metadata":           meta,
            "active":             active,
            "embedding_approved": False,
            "release_id":         release_id,
        })
    return chunks


def main():
    print(f"Reading: {INPUT_PATH}")
    with INPUT_PATH.open(encoding="utf-8") as f:
        db = json.load(f)

    release_id = db.get("release_id", "knowledge-v1-20261028")
    documents  = db.get("documents", [])
    print(f"Documents: {len(documents)}  release_id: {release_id}")

    all_chunks = []
    split_docs = 0
    for doc in documents:
        chunks = chunk_document(doc, release_id)
        if len(chunks) > 1:
            split_docs += 1
        all_chunks.extend(chunks)

    ids = [c["chunk_id"] for c in all_chunks]
    assert len(ids) == len(set(ids)), "Duplicate chunk_id detected!"
    assert all(not c["embedding_approved"] for c in all_chunks), \
        "embedding_approved must be False for all chunks at build time"

    output = {
        "release_id":            release_id,
        "generated_at":          "2026-10-28",
        "split_threshold_chars": SPLIT_THRESHOLD,
        "total_documents":       len(documents),
        "total_chunks":          len(all_chunks),
        "paragraph_split_docs":  split_docs,
        "chunks":                all_chunks,
    }

    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Chunks written: {len(all_chunks)}  (paragraph-split docs: {split_docs})")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
