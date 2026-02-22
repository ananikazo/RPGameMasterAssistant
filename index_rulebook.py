"""Index PDF rulebook pages into ChromaDB for semantic search.

Reads PDF files from GM_VAULT_PATH, extracts text using semantic chunking
(500-1000 tokens per chunk with ~100-token overlap), and stores chunks in
the 'rulebook' ChromaDB collection. Each chunk's metadata includes a
comma-separated list of all PDF page numbers it spans. Performs incremental
indexing based on file modification timestamps.

Usage:
    GM_VAULT_PATH=./vault GM_CHROMA_PATH=./chroma_db python index_rulebook.py
"""
import chromadb
import os
import re
from pypdf import PdfReader
from index_utils import load_timestamps, save_timestamps, get_file_mtime

# Configuration from environment variables
VAULT_PATH = os.environ.get("GM_VAULT_PATH", "./vault")
CHROMA_DB_PATH = os.environ.get("GM_CHROMA_PATH", "./chroma_db")
TIMESTAMP_FILE = "index_rulebook_timestamps.json"

# Chunking parameters (~4 characters per token)
TARGET_CHUNK_CHARS = 3000  # ~750 tokens (mid-range of 500–1000 target)
OVERLAP_CHARS = 400        # ~100 tokens


def build_semantic_chunks(pages_text, target_chars=TARGET_CHUNK_CHARS, overlap_chars=OVERLAP_CHARS):
    """Split PDF pages into semantic chunks with overlap.

    Paragraphs are kept intact; chunks accumulate paragraphs until the
    target size is reached. Adjacent chunks share a trailing overlap so
    that topics spanning a boundary appear in both chunks.

    Args:
        pages_text: list of (page_num, text) tuples with 1-based page numbers.
        target_chars: approximate target size of each chunk in characters.
        overlap_chars: approximate overlap between adjacent chunks in characters.

    Returns:
        list of dicts with keys:
            "text"  – chunk content as a string
            "pages" – sorted list of 1-based page numbers contained in the chunk
    """
    # Build a flat sequence of (paragraph, page_num) pairs
    paragraphs = []
    for page_num, text in pages_text:
        for para in re.split(r'\n\s*\n', text):
            para = para.strip()
            if len(para) > 20:  # drop very short/empty fragments
                paragraphs.append((para, page_num))

    if not paragraphs:
        return []

    chunks = []
    start = 0

    while start < len(paragraphs):
        chunk_paras = []
        chunk_pages = set()
        current_len = 0
        end = start

        # Accumulate paragraphs until we reach the target size
        while end < len(paragraphs):
            para, page_num = paragraphs[end]
            para_len = len(para) + 2  # +2 for the "\n\n" separator
            if current_len + para_len > target_chars and chunk_paras:
                break
            chunk_paras.append(para)
            chunk_pages.add(page_num)
            current_len += para_len
            end += 1

        # Edge case: a single paragraph exceeds the target – include it anyway
        if end == start:
            para, page_num = paragraphs[start]
            chunk_paras = [para]
            chunk_pages = {page_num}
            end = start + 1

        chunk_text = "\n\n".join(chunk_paras)
        if chunk_text.strip():
            chunks.append({
                "text": chunk_text,
                "pages": sorted(chunk_pages),
            })

        # Step back by however many trailing paragraphs fit within overlap_chars
        # so the next chunk starts with some shared context
        overlap_len = 0
        overlap_count = 0
        for k in range(end - 1, start - 1, -1):
            pl = len(paragraphs[k][0]) + 2
            if overlap_len + pl > overlap_chars:
                break
            overlap_len += pl
            overlap_count += 1

        next_start = end - overlap_count
        start = max(next_start, start + 1)  # always advance at least one step

    return chunks


# Create Chroma client
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
rulebook_collection = client.get_or_create_collection(name="rulebook")

rulebook_docs = []
rulebook_metas = []
rulebook_ids = []

print(f"Reading rulebook from: {VAULT_PATH}")
timestamps = load_timestamps(TIMESTAMP_FILE)

# If the collection is empty, force a full re-index regardless of saved timestamps.
# This covers cases where the DB was cleared without removing the timestamp file,
# or where a previous run failed after saving timestamps but before writing to ChromaDB.
if rulebook_collection.count() == 0 and timestamps:
    print("Collection is empty – forcing full re-index.")
    timestamps = {}

for root, dirs, files in os.walk(VAULT_PATH):
    for file in files:
        if not file.endswith(".pdf"):
            continue

        filepath = os.path.join(root, file)
        current_mtime = get_file_mtime(filepath)

        # Skip if unchanged
        if filepath in timestamps and timestamps[filepath] == current_mtime:
            timestamps[filepath] = current_mtime
            continue

        status = "NEW" if filepath not in timestamps else "CHANGED"
        print(f"  [{status}] {file}")

        timestamps[filepath] = current_mtime

        try:
            pdf = PdfReader(filepath)

            # Delete all existing chunks for this file before re-indexing.
            # Guard against empty-collection errors (e.g. first run with no
            # prior documents) by isolating the lookup/delete in its own
            # try-except – nothing to delete on an empty collection anyway.
            try:
                existing = rulebook_collection.get(where={"path": filepath})
                if existing["ids"]:
                    rulebook_collection.delete(ids=existing["ids"])
            except Exception:
                pass  # Collection is empty; no existing chunks to remove

            # Extract text per page (1-based), skipping blank pages
            pages_text = []
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    pages_text.append((page_num, text))

            # Build semantic chunks across all pages
            chunks = build_semantic_chunks(pages_text)

            for chunk_idx, chunk in enumerate(chunks):
                rulebook_docs.append(chunk["text"])
                rulebook_metas.append({
                    "filename": file,
                    "path": filepath,
                    # ChromaDB metadata values must be scalars; store as CSV string
                    "pages": ",".join(str(p) for p in chunk["pages"]),
                })
                rulebook_ids.append(f"{filepath}_chunk_{chunk_idx}")

            print(f"  PDF processed: {file} ({len(pdf.pages)} pages → {len(chunks)} chunks)")
        except Exception as e:
            print(f"  Error with {file}: {e}")

save_timestamps(timestamps, TIMESTAMP_FILE)

# Index in Chroma
if rulebook_docs:
    rulebook_collection.add(documents=rulebook_docs, metadatas=rulebook_metas, ids=rulebook_ids)
    print(f"\n✓ Rulebook indexed: {len(rulebook_docs)} chunks")
else:
    print("\n✓ No changes - nothing to index")

print("Done!")
