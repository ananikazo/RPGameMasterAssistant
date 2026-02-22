"""Reset the campaign ChromaDB collection and timestamp file for a clean re-index.

Deletes the 'campaign' collection from ChromaDB and removes the corresponding
timestamp JSON file. Run this before a full re-index of campaign notes.

Usage:
    GM_CHROMA_PATH=./chroma_db python index_clear_campaign.py
"""
import chromadb
import os

# Configuration from environment variables
CHROMA_DB_PATH = os.environ.get("GM_CHROMA_PATH", "./chroma_db")

client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Delete collection
try:
    client.delete_collection(name="campaign")
    print("✓ Collection 'campaign' deleted")
except Exception:
    print("⚠ Collection 'campaign' does not exist")

# Delete timestamp file
timestamp_file = "index_campaign_timestamps.json"
if os.path.exists(timestamp_file):
    os.remove(timestamp_file)
    print(f"✓ {timestamp_file} deleted")
else:
    print(f"⚠ {timestamp_file} not found")

print("\n✓ Campaign database and timestamps cleared!")
