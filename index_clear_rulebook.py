"""Reset the rulebook ChromaDB collection and timestamp file for a clean re-index.

Deletes the 'rulebook' collection from ChromaDB and removes the corresponding
timestamp JSON file. Run this before a full re-index of rulebook PDFs.

Usage:
    GM_CHROMA_PATH=./chroma_db python index_clear_rulebook.py
"""
import chromadb
import os

# Configuration from environment variables
CHROMA_DB_PATH = os.environ.get("GM_CHROMA_PATH", "./chroma_db")

client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Delete collection
try:
    client.delete_collection(name="rulebook")
    print("✓ Collection 'rulebook' deleted")
except Exception:
    print("⚠ Collection 'rulebook' does not exist")

# Delete timestamp file
timestamp_file = "index_rulebook_timestamps.json"
if os.path.exists(timestamp_file):
    os.remove(timestamp_file)
    print(f"✓ {timestamp_file} deleted")
else:
    print(f"⚠ {timestamp_file} not found")

print("\n✓ Rulebook database and timestamps cleared!")
