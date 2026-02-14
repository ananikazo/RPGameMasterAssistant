import os
import anthropic
import chromadb
import textwrap
import sys
import io

# UTF-8 encoding for input/output
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configuration from environment variables
CHROMA_DB_PATH = os.environ.get("GM_CHROMA_PATH", "./chroma_db")

# API Key
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Load Chroma database
print("Loading database...")
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
campaign_collection = chroma_client.get_collection(name="campaign")
rulebook_collection = chroma_client.get_collection(name="rulebook")

def classify_complexity(question, client):
    """Let Claude determine question complexity"""
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": f"""Classify this question's complexity:
- simple (3-5 documents): Specific question about one person/rule
- medium (8-12 documents): Comparisons, connections, multiple aspects
- complex (15-20 documents): Lists, overviews, "all X", comprehensive analysis

Examples:
- "Who is John?" → simple
- "List all classes" → complex
- "Compare fighter and wizard" → medium

Question: {question}

Answer with only one word: simple, medium, or complex"""
        }]
    )
    
    complexity = message.content[0].text.strip().lower()
    
    if complexity == "simple":
        return 5
    elif complexity == "complex":
        return 20
    else:  # medium
        return 12

print("GM Assistant ready! (Type 'quit' to exit)\n")

# Interactive loop
while True:
    print("\n[1] Campaign question")
    print("[2] Rules question")
    print("[3] Exit")
    
    mode = input("\nSelect mode (1/2/3): ").strip()
    
    if mode == "3" or mode.lower() == "quit":
        break
    
    if mode not in ["1", "2"]:
        print("Invalid selection!")
        continue
    
    question = input("\nYour question: ")
    
    # Determine complexity
    num_results = classify_complexity(question, client)
    print(f"[Complexity: {num_results} documents]")
    
    if mode == "1":  # Campaign only
        question_type = "campaign"
        
        campaign_results = campaign_collection.query(
            query_texts=[question],
            n_results=num_results
        )
        
        # Build context from campaign only
        vault_content = ""
        for i, doc in enumerate(campaign_results['documents'][0]):
            filename = campaign_results['metadatas'][0][i]['filename']
            vault_content += f"\n\n=== CAMPAIGN: {filename} ===\n{doc}"
        
        # Debug output
        print("\n=== DEBUG: Found documents ===")
        for i, meta in enumerate(campaign_results['metadatas'][0]):
            print(f"{i+1}. Campaign: {meta.get('filename', 'unknown')}")
        print("=== DEBUG END ===\n")
        
    else:  # Rules only
        question_type = "rules"
        
        rulebook_results = rulebook_collection.query(
            query_texts=[question],
            n_results=num_results
        )
        
        # Build context from rulebook only
        vault_content = ""
        for i, doc in enumerate(rulebook_results['documents'][0]):
            meta = rulebook_results['metadatas'][0][i]
            filename = meta.get('filename', 'Rulebook')
            page = meta.get('page', 'N/A')
            vault_content += f"\n\n=== RULEBOOK: {filename} Page {page} ===\n{doc}"
        
        # Debug output
        print("\n=== DEBUG: Found documents ===")
        for i, meta in enumerate(rulebook_results['metadatas'][0]):
            print(f"{i+1}. Rulebook: {meta.get('filename', 'unknown')} p.{meta.get('page', 'N/A')}")
        print("=== DEBUG END ===\n")
    
    # Ask Claude
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": f"""You are a tabletop RPG game master assistant.
Answer precisely and concisely. Keep responses short unless explicitly asked for details.
Respond in plain text without markdown formatting.

Context hints:
- Text in [[Name]] are note links to other documents
- Answer based only on the provided context

Relevant context:
{vault_content}

Question: {question}"""
        }]
    )
    
    answer = message.content[0].text
    
    try:
        formatted = textwrap.fill(answer, width=80)
        print(f"\nAnswer:\n{formatted}")
    except UnicodeEncodeError:
        clean = answer.encode('utf-8', errors='replace').decode('utf-8')
        formatted = textwrap.fill(clean, width=80)
        print(f"\nAnswer:\n{formatted}")

print("\nGoodbye!")