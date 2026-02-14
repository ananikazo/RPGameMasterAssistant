import chromadb
from sentence_transformers import SentenceTransformer
import os
import json

# Configuration from environment variables
VAULT_PATH = os.environ.get("GM_VAULT_PATH", "./vault")
CHROMA_DB_PATH = os.environ.get("GM_CHROMA_PATH", "./chroma_db")
TIMESTAMP_FILE = "index_campaign_timestamps.json"

def load_timestamps():
    if os.path.exists(TIMESTAMP_FILE):
        with open(TIMESTAMP_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_timestamps(timestamps):
    with open(TIMESTAMP_FILE, 'w') as f:
        json.dump(timestamps, f)

def get_file_mtime(filepath):
    return os.path.getmtime(filepath)

# Load embedding model
print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')

# Create Chroma client
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
campaign_collection = client.get_or_create_collection(name="campaign")

campaign_docs = []
campaign_metas = []
campaign_ids = []

print(f"Reading campaign notes from: {VAULT_PATH}")
timestamps = load_timestamps()

for root, dirs, files in os.walk(VAULT_PATH):
    for file in files:
        if not file.endswith(".md"):
            continue
            
        filepath = os.path.join(root, file)
        current_mtime = get_file_mtime(filepath)

        # Skip if unchanged
        if filepath in timestamps and timestamps[filepath] == current_mtime:
            timestamps[filepath] = current_mtime
            continue

        # Delete and re-index
        try:
            campaign_collection.delete(ids=[filepath])
        except:
            pass

        # Debug: Show what's being indexed
        status = "NEW" if filepath not in timestamps else "CHANGED"
        print(f"  [{status}] {file}")

        timestamps[filepath] = current_mtime

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            campaign_docs.append(content)
            campaign_metas.append({"filename": file, "path": filepath})
            campaign_ids.append(filepath)

save_timestamps(timestamps)

# Index in Chroma
if campaign_docs:
    campaign_collection.add(documents=campaign_docs, metadatas=campaign_metas, ids=campaign_ids)
    print(f"\n✓ Campaign indexed: {len(campaign_docs)} documents")
else:
    print("\n✓ No changes - nothing to index")

print("Done!")