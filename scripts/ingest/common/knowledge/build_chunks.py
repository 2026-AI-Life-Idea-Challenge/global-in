"""
scripts/ingest/common/knowledge/build_chunks.py

Produces knowledge_chunks.json from knowledge_release.json.

Chunking strategy:
  Plain-text documents (<= SPLIT_THRESHOLD chars):
    → single chunk (ordinal 0), split_strategy="single"
  Plain-text documents (> SPLIT_THRESHOLD chars):
    → paragraph-split on double newlines, split_strategy="paragraph"
  JSON-structured documents (text starts with '{' or '['):
    → extract natural-language fields: findings, interpretation, limitation
    → concatenate into one chunk, split_strategy="json_nl_extract"
    → metadata.raw_json=True

Output schema matches knowledge_chunks table (20261028_knowledge_contract.sql):
  chunk_id, document_id, revision_id, ordinal, body, content_sha256,
  metadata, active, embedding_approved (always False), release_id
"""

import hashlib
import json
import re
from pathlib import Path

SPLIT_THRESHOLD = 2000
MIN_PARA = 80

REPO_ROOT   = Path(__file__).resolve().parents[4]
RELEASE_DIR = REPO_ROOT / "data" / "processed" / "knowledge" / "20261028"
INPUT_PATH  = RELEASE_DIR / "knowledge_release.json"
OUTPUT_PATH = RELEASE_DIR / "knowledge_chunks.json"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_paragraphs(text: str) -> list:
    raw = re.split(r"\n{2,}", text.strip())
    merged, buf = [], ""
    for para in raw:
        para = para.strip()
        if not para:
            continue
        buf = (buf + "\n\n" + para) if buf else para
        if len(buf) >= MIN_PARA:
            merged.append(buf)
            buf = ""
    if buf:
        if merged:
            merged[-1] += "\n\n" + buf
        else:
            merged.append(buf)
    return merged or [text.strip()]


def extract_json_nl(text: str):
    """
    Parse JSON-structured policy text and extract natural-language fields.
    Returns (body: str, extra_meta: dict) or (None, {}) if parse fails.
    """
    try:
        parsed = json.loads(text)
    except Exception:
        return None, {}

    if not isinstance(parsed, dict):
        return None, {}

    parts = []

    # findings: list of Korean-language interpretation strings
    findings = parsed.get("findings")
    if findings:
        if isinstance(findings, list):
            parts.append("\n".join(f"- {f}" for f in findings if f))
        elif isinstance(findings, str) and findings.strip():
            parts.append(findings.strip())

    # interpretation: Japanese/Korean mixed interpretation note
    interp = parsed.get("interpretation")
    if interp and isinstance(interp, str) and interp.strip():
        parts.append(interp.strip())

    # limitation: scope limitation note
    limit = parsed.get("limitation")
    if limit and isinstance(limit, str) and limit.strip():
        parts.append(f"[적용 범위] {limit.strip()}")

    # application_scope summary (structured → brief label)
    scope = parsed.get("application_scope", {})
    if isinstance(scope, dict):
        scope_parts = []
        if scope.get("application_type"):
            scope_parts.append(f"신청 유형: {scope['application_type']}")
        if scope.get("school_category"):
            scope_parts.append(f"학교 유형: {scope['school_category']}")
        if scope.get("school_classification"):
            scope_parts.append(f"학교 분류: {scope['school_classification']}")
        if scope_parts:
            parts.insert(0, " / ".join(scope_parts))

    body = "\n\n".join(parts).strip()
    extra_meta = {
        "raw_json": True,
        "json_fields_extracted": ["application_scope", "findings", "interpretation", "limitation"],
    }
    return body if body else None, extra_meta


def chunk_document(doc, release_id):
    doc_id = doc["document_id"]
    rev_id = doc["revision_id"]
    text   = (doc.get("text") or "").strip()
    active = doc.get("active", True)

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

    # JSON-structured documents → NL extraction
    if text.startswith("{") or text.startswith("["):
        body, extra_meta = extract_json_nl(text)
        if body:
            meta = {**base_meta, "split_strategy": "json_nl_extract", **extra_meta}
            return [{
                "chunk_id":           f"{doc_id}::{rev_id}::chunk0",
                "document_id":        doc_id,
                "revision_id":        rev_id,
                "ordinal":            0,
                "body":               body,
                "content_sha256":     sha256(body),
                "metadata":           meta,
                "active":             active,
                "embedding_approved": False,
                "release_id":         release_id,
            }]
        # fallback: treat as plain text if extraction yields nothing
        segments, strategy = [text], "single"
    elif len(text) <= SPLIT_THRESHOLD:
        segments, strategy = [text], "single"
    else:
        segments, strategy = split_paragraphs(text), "paragraph"

    chunks = []
    for ordinal, segment in enumerate(segments):
        segment = segment.strip()
        if not segment:
            continue
        meta = {**base_meta, "split_strategy": strategy}
        chunks.append({
            "chunk_id":           f"{doc_id}::{rev_id}::chunk{ordinal}",
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
    stats = {"single": 0, "paragraph": 0, "json_nl_extract": 0}
    for doc in documents:
        chunks = chunk_document(doc, release_id)
        for c in chunks:
            stats[c["metadata"]["split_strategy"]] = \
                stats.get(c["metadata"]["split_strategy"], 0) + 1
        all_chunks.extend(chunks)

    ids = [c["chunk_id"] for c in all_chunks]
    assert len(ids) == len(set(ids)), "Duplicate chunk_id detected!"
    assert all(not c["embedding_approved"] for c in all_chunks), \
        "embedding_approved must be False at build time"

    output = {
        "release_id":            release_id,
        "generated_at":          "2026-10-28",
        "split_threshold_chars": SPLIT_THRESHOLD,
        "total_documents":       len(documents),
        "total_chunks":          len(all_chunks),
        "strategy_counts":       stats,
        "chunks":                all_chunks,
    }

    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Chunks written: {len(all_chunks)}")
    print(f"Strategy breakdown: {stats}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
