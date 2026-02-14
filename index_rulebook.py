import chromadb
from sentence_transformers import SentenceTransformer
import os
from pypdf import PdfReader
import json

# Configuration from environment variables
VAULT_PATH = os.environ.get("GM_VAULT_PATH", "./vault")
CHROMA_DB_PATH = os.environ.get("GM_CHROMA_PATH", "./chroma_db")
TIMESTAMP_FILE = "index_rulebook_timestamps.json"

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
rulebook_collection = client.get_or_create_collection(name="rulebook")

rulebook_docs = []
rulebook_metas = []
rulebook_ids = []

print(f"Reading rulebook from: {VAULT_PATH}")
timestamps = load_timestamps()

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
                except:
                    pass
            
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

save_timestamps(timestamps)

# Index in Chroma
if rulebook_docs:
    rulebook_collection.add(documents=rulebook_docs, metadatas=rulebook_metas, ids=rulebook_ids)
    print(f"\n✓ Rulebook indexed: {len(rulebook_docs)} documents")
else:
    print("\n✓ No changes - nothing to index")

print("Done!")