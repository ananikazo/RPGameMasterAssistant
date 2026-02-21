"""Index PDF rulebook pages into ChromaDB for semantic search.

Reads PDF files from GM_VAULT_PATH, extracts each page as a separate
document, and stores them in the 'rulebook' ChromaDB collection.
Performs incremental indexing based on file modification timestamps.

Usage:
    GM_VAULT_PATH=./vault GM_CHROMA_PATH=./chroma_db python index_rulebook.py
"""
import chromadb
import os
from pypdf import PdfReader
from index_utils import load_timestamps, save_timestamps, get_file_mtime

# Configuration from environment variables
VAULT_PATH = os.environ.get("GM_VAULT_PATH", "./vault")
CHROMA_DB_PATH = os.environ.get("GM_CHROMA_PATH", "./chroma_db")
TIMESTAMP_FILE = "index_rulebook_timestamps.json"

# Create Chroma client
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
rulebook_collection = client.get_or_create_collection(name="rulebook")

rulebook_docs = []
rulebook_metas = []
rulebook_ids = []

print(f"Reading rulebook from: {VAULT_PATH}")
timestamps = load_timestamps(TIMESTAMP_FILE)

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

        # Debug: Show what's being indexed
        status = "NEW" if filepath not in timestamps else "CHANGED"
        print(f"  [{status}] {file}")

        timestamps[filepath] = current_mtime

        try:
            pdf = PdfReader(filepath)
            
            # Delete old PDF pages
            for page_num in range(len(pdf.pages)):
                try:
                    rulebook_collection.delete(ids=[f"{filepath}_page_{page_num + 1}"])
                except Exception:
                    pass  # Page does not exist yet – safely ignorable
            
            # Each page as separate document
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text.strip():
                    rulebook_docs.append(text)
                    rulebook_metas.append({
                        "filename": file,
                        "page": page_num + 1,
                        "path": filepath
                    })
                    rulebook_ids.append(f"{filepath}_page_{page_num + 1}")
            
            print(f"  PDF processed: {file} ({len(pdf.pages)} pages)")
        except Exception as e:
            print(f"  Error with {file}: {e}")

save_timestamps(timestamps, TIMESTAMP_FILE)

# Index in Chroma
if rulebook_docs:
    rulebook_collection.add(documents=rulebook_docs, metadatas=rulebook_metas, ids=rulebook_ids)
    print(f"\n✓ Rulebook indexed: {len(rulebook_docs)} documents")
else:
    print("\n✓ No changes - nothing to index")

print("Done!")