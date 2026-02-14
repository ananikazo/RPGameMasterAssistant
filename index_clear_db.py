import chromadb
import os

# Configuration from environment variables
CHROMA_DB_PATH = os.environ.get("GM_CHROMA_PATH", "./chroma_db")

client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Delete collections
try:
    client.delete_collection(name="campaign")
    print("✓ Collection 'campaign' deleted")
except:
    print("⚠ Collection 'campaign' does not exist")

try:
    client.delete_collection(name="rulebook")
    print("✓ Collection 'rulebook' deleted")
except:
    print("⚠ Collection 'rulebook' does not exist")

# Delete timestamps
for timestamp_file in ["index_campaign_timestamps.json", "index_rulebook_timestamps.json"]:
    if os.path.exists(timestamp_file):
        os.remove(timestamp_file)
        print(f"✓ {timestamp_file} deleted")
    else:
        print(f"⚠ {timestamp_file} not found")

print("\n✓ Database and timestamps cleared!")