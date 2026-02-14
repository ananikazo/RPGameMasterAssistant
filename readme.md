# GM Assistant

An AI-powered game master assistant for tabletop RPGs using Claude AI and vector database technology. Helps GMs manage campaign notes, NPCs, locations, and rules during game sessions with intelligent semantic search.

## Features

- **Vector Database Search**: Semantic search across campaign notes using Chroma DB
- **Separate Collections**: Campaign content and rulebooks indexed separately
- **Incremental Indexing**: Only changed files are re-indexed for efficiency
- **Intelligent Complexity Detection**: Automatically scales search results (5-20 documents) based on question complexity
- **Obsidian Integration**: Works seamlessly with Obsidian markdown notes
- **Cost Optimized**: ~95% reduction in API costs vs. naive full-context approach

## Tech Stack

- Python 3.8+
- Claude API (Anthropic)
- Chroma vector database
- Sentence Transformers for embeddings
- PyPDF for rulebook indexing

## Prerequisites

- Python 3.8 or higher
- Claude API key from [Anthropic](https://console.anthropic.com/)
- Campaign notes in Markdown format
- (Optional) Rulebook in PDF format

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/gm-assistant.git
cd gm-assistant
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your paths and API key
```

## Configuration

Create a `.env` file with the following variables:
```bash
# Path to your campaign notes (Obsidian vault or markdown folder)
GM_VAULT_PATH=/path/to/your/vault

# Path to Chroma database (will be created if it doesn't exist)
GM_CHROMA_PATH=./chroma_db

# Your Anthropic API key
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Alternatively, export these as environment variables in your shell.

## Usage

### Initial Setup

1. **Index your campaign notes** (Markdown files):
```bash
python3 index_campaign.py
```

2. **Index your rulebook** (PDF files - optional):
```bash
python3 index_rulebook.py
```

### Running the Assistant

Start the interactive assistant:
```bash
python3 gm_assistant.py
```

Select mode:
- `[1]` Campaign questions - searches only campaign notes
- `[2]` Rules questions - searches only rulebook
- `[3]` Exit

The assistant will automatically determine question complexity and retrieve the appropriate number of documents (5-20).

### Updating the Index

Re-run the indexing scripts after adding or modifying notes:
```bash
python3 index_campaign.py  # Updates only changed markdown files
python3 index_rulebook.py  # Updates only changed PDFs
```

### Clearing the Database

To completely reset the database:
```bash
python3 index_clear_db.py
```

## How It Works

This project implements a RAG (Retrieval-Augmented Generation) architecture:

1. **Indexing**: Your campaign notes and rulebooks are converted into vector embeddings using Sentence Transformers
2. **Storage**: Embeddings are stored in a Chroma vector database with separate collections for campaign and rules
3. **Retrieval**: When you ask a question, the system searches for semantically similar documents
4. **Generation**: Claude generates answers based only on the retrieved context

## Cost Optimization

- **Incremental indexing**: Only processes changed files
- **Targeted retrieval**: Sends only relevant documents to Claude (not entire vault)
- **Typical costs**: ~$0.05-0.20 per game session vs. $2-5 without vector search

## Example Workflow

1. Prepare campaign notes in Obsidian or markdown files
2. Index notes: `python3 index_campaign.py`
3. During game session: Run `python3 gm_assistant.py`
4. Ask questions like:
   - "Who is the mayor of Riverside?"
   - "What abilities does a level 3 ranger have?"
   - "List all NPCs in the thieves guild"

## Limitations

- Requires Claude API access (paid service)
- Works best with structured, well-organized notes
- PDF indexing quality depends on PDF text extraction
- Obsidian links (`[[Name]]`) are preserved but not automatically followed

## Contributing

Contributions welcome! Please open an issue.

## License

MIT License - see LICENSE file for details

## Acknowledgments

Powered by:
- [Anthropic Claude](https://www.anthropic.com/)
- [Chroma](https://www.trychroma.com/)
- [Sentence Transformers](https://www.sbert.net/)