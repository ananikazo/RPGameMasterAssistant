"""Interactive GM assistant using Claude API and ChromaDB for semantic search.

Presents a menu to query either campaign notes or rulebook content.
Retrieves relevant context via vector search and answers via Claude.

Usage:
    GM_CHROMA_PATH=./chroma_db ANTHROPIC_API_KEY=... python gm-assistant.py
"""
import os
import sys
import io
import textwrap

import anthropic
import chromadb

# UTF-8 encoding for input/output
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configuration from environment variables
CHROMA_DB_PATH = os.environ.get("GM_CHROMA_PATH", "./chroma_db")

# Constants
MODEL_NAME = "claude-sonnet-4-5-20250929"
COMPLEXITY_SIMPLE_DOCS = 5
COMPLEXITY_MEDIUM_DOCS = 12
COMPLEXITY_COMPLEX_DOCS = 20
CLASSIFY_MAX_TOKENS = 50
ANSWER_MAX_TOKENS = 2048
TERMINAL_WIDTH = 80


def classify_complexity(question: str, client: anthropic.Anthropic) -> int:
    """Classify question complexity and return the number of documents to retrieve.

    Returns 5 for simple, 12 for medium, and 20 for complex questions.
    """
    message = client.messages.create(
        model=MODEL_NAME,
        max_tokens=CLASSIFY_MAX_TOKENS,
        messages=[{
            "role": "user",
            "content": (
                f'Classify this question\'s complexity:\n'
                f'- simple (3-5 documents): Specific question about one person/rule\n'
                f'- medium (8-12 documents): Comparisons, connections, multiple aspects\n'
                f'- complex (15-20 documents): Lists, overviews, "all X", comprehensive analysis\n'
                f'\n'
                f'Examples:\n'
                f'- "Who is John?" \u2192 simple\n'
                f'- "List all classes" \u2192 complex\n'
                f'- "Compare fighter and wizard" \u2192 medium\n'
                f'\n'
                f'Question: {question}\n'
                f'\n'
                f'Answer with only one word: simple, medium, or complex'
            ),
        }]
    )

    complexity = message.content[0].text.strip().lower()

    if complexity == "simple":
        return COMPLEXITY_SIMPLE_DOCS
    elif complexity == "complex":
        return COMPLEXITY_COMPLEX_DOCS
    else:  # medium
        return COMPLEXITY_MEDIUM_DOCS


def query_collection(
    collection: chromadb.Collection,
    question: str,
    num_results: int,
    source_type: str,
) -> tuple:
    """Query a ChromaDB collection and build a context string.

    Args:
        collection: The ChromaDB collection to query.
        question: The user's question as query text.
        num_results: Number of documents to retrieve.
        source_type: Label for the source, e.g. "CAMPAIGN" or "RULEBOOK".

    Returns:
        A tuple of (context_string, list_of_metadata_dicts).
    """
    results = collection.query(
        query_texts=[question],
        n_results=num_results,
    )
    context = ""
    for i, doc in enumerate(results['documents'][0]):
        meta = results['metadatas'][0][i]
        label = f"{source_type}: {meta.get('filename', 'unknown')}"
        if source_type == "RULEBOOK":
            label += f" Page {meta.get('page', 'N/A')}"
        context += f"\n\n=== {label} ===\n{doc}"
    return context, results['metadatas'][0]


def print_debug_sources(metadatas: list, source_type: str) -> None:
    """Print debug information about retrieved source documents."""
    print("\n=== DEBUG: Found documents ===")
    for i, meta in enumerate(metadatas):
        name = meta.get('filename', 'unknown')
        page = f" p.{meta.get('page', 'N/A')}" if source_type == "RULEBOOK" else ""
        print(f"{i + 1}. {source_type}: {name}{page}")
    print("=== DEBUG END ===\n")


def get_answer(question: str, context: str, client: anthropic.Anthropic) -> str:
    """Send question with context to Claude and return the answer text."""
    prompt = (
        "You are a tabletop RPG game master assistant.\n"
        "Answer precisely and concisely. Keep responses short unless explicitly asked for details.\n"
        "Respond in plain text without markdown formatting.\n"
        "\n"
        "Context hints:\n"
        "- Text in [[Name]] are note links to other documents\n"
        "- Answer based only on the provided context\n"
        "\n"
        f"Relevant context:\n{context}\n"
        "\n"
        f"Question: {question}"
    )
    message = client.messages.create(
        model=MODEL_NAME,
        max_tokens=ANSWER_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def print_answer(answer: str) -> None:
    """Format and print the answer, handling encoding issues gracefully."""
    try:
        print(f"\nAnswer:\n{textwrap.fill(answer, width=TERMINAL_WIDTH)}")
    except UnicodeEncodeError:
        clean = answer.encode('utf-8', errors='replace').decode('utf-8')
        print(f"\nAnswer:\n{textwrap.fill(clean, width=TERMINAL_WIDTH)}")


if __name__ == "__main__":
    # API client
    ai_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # Load Chroma database
    print("Loading database...")
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    campaign_collection = chroma_client.get_collection(name="campaign")
    rulebook_collection = chroma_client.get_collection(name="rulebook")

    print("GM Assistant ready! (Type 'quit' to exit)\n")

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

        question = input("\nYour question: ").strip()
        if not question:
            print("Please enter a question.")
            continue

        num_results = classify_complexity(question, ai_client)
        print(f"[Complexity: {num_results} documents]")

        if mode == "1":
            context, metadatas = query_collection(
                campaign_collection, question, num_results, "CAMPAIGN"
            )
        else:
            context, metadatas = query_collection(
                rulebook_collection, question, num_results, "RULEBOOK"
            )

        source_type = "CAMPAIGN" if mode == "1" else "RULEBOOK"
        print_debug_sources(metadatas, source_type)

        answer = get_answer(question, context, ai_client)
        print_answer(answer)

    print("\nGoodbye!")
