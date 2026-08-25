# Agora AI
### Community Conversation Intelligence

**Agora AI** is a local-first, privacy-focused community conversation intelligence platform designed to extract structured insights, analytical metrics, and grounded answers from unstructured community chat exports.

Currently supporting exported WhatsApp text logs, Agora AI combines deterministic relational analytics in SQLite, vector similarity retrieval in ChromaDB, and local LLM reasoning via Ollama to make community knowledge searchable and actionable.

---

## 🎯 Why Agora AI?

- **Manual Review Does Not Scale**: High-volume community groups generate thousands of messages per week. Manually surfacing key topics, user pain points, or recurring themes is time-consuming.
- **Chat Exports Are Unstructured**: Raw export files consist of unstructured text streams with inconsistent datetime formats, inline system notices, and thoughts split across multi-line messages.
- **Keyword Search Misses Context**: Conventional substring matching fails on semantic intent, indirect phrasing, synonyms, and conversational context spanning multiple messages.
- **Hybrid Analytical Approach**: Agora AI pairs deterministic SQL queries for exact numerical statistics (member counts, hourly density, daily volume curves) with vector retrieval (ChromaDB + Sentence Transformers) and local LLM reasoning (Qwen 2.5) for semantic Q&A.

---

## 🌟 Key Features

- **🔒 Local-First Processing**: By default, chat processing is performed locally. LLM inference runs through Ollama and embeddings are generated locally using Sentence Transformers; the application does not use a cloud LLM API for these operations.
- **💬 Grounded RAG Chat Copilot**: Ask natural language questions grounded in community discussion logs. Produces structured reasoning outputs (`Observation`, `Inference`, `Recommendation`) alongside confidence ratings and collapsible citation evidence.
- **🧩 Context-Aware Conversation Chunking**: Groups messages dynamically using a Strategy Pattern (`ConversationChunker`) based on 15-minute time gaps or 50-message density limits, maintaining conversational context rather than evaluating single messages in isolation.
- **📊 Analytics Dashboard**: Visualizes total members, parsed messages, top contributors, daily message volume curves, and 24-hour hourly density distributions with visual axis scales and explanatory notes.
- **📑 Automated Intelligence Reports**: Synthesizes executive summaries, discussed topics, community sentiment/mood, key trends, active contributors, and strategic recommendations using local LLM synthesis.
- **🔎 Conversation Explorer**: Full-text keyword search, pagination (`LIMIT`/`OFFSET`), relative time filters (Last 1h, 24h, 7d, 30d, Custom range), sender filtering, media detection, and streaming exports to `.txt` and `.json`.
- **🎨 Modern Dashboard Design**: Notion and Linear inspired UI with Light (default) and Dark theme toggles, polished typography (`Inter`), and clean component hierarchy.

---

## 🏗️ Architecture & Tech Stack

```
                                +-------------------+
                                |   React + Vite    |
                                |  TypeScript UI    |
                                +---------+---------+
                                          | REST API
                                          v
                                +---------+---------+
                                |  FastAPI Backend  |
                                +----+----+----+----+
                                     |    |    |
            +------------------------+    |    +-------------------------+
            |                             |                              |
            v                             v                              v
  +---------+---------+         +---------+---------+          +---------+---------+
  | SQLite Database   |         | ChromaDB Vector   |          | Local Ollama      |
  | (Relational Logs) |         | Store (Embeddings)|          | (Qwen 2.5 LLM)    |
  +-------------------+         +-------------------+          +-------------------+
```

- **Frontend**: React 18, TypeScript, Vite, Lucide Icons, Custom CSS Tokens
- **Backend**: FastAPI, SQLAlchemy, Pydantic, Uvicorn
- **Vector Store**: ChromaDB (`PersistentClient`)
- **Embeddings**: `sentence-transformers` (`all-MiniLM-L6-v2`)
- **LLM Engine**: Ollama (`qwen2.5:1.5b`)
- **Database**: SQLite (`community_intelligence.db`)

---

## 🧠 RAG Pipeline Architecture

```
WhatsApp Export (.txt)
  │
  ├──► Parsing & Normalization (Regex matching timestamps & multi-line continuations)
  │
  ├──► Strategy-Pattern Conversation Chunking (15-min gap / 50-message windows)
  │
  ├──► SQLite Relational Storage (Persists Sources, Conversations, and Messages)
  │
  ├──► Vector Embedding (Dense 384-d vectors via Sentence Transformers)
  │
  ├──► ChromaDB Indexing (Stores vector embeddings & thread metadata)
  │
  └──► Query Execution Pipeline:
        1. Embed User Query via Sentence Transformers
        2. Query ChromaDB for Vector Similarity (Top-K matching chunk IDs)
        3. Reconstruct Complete Chronological Threads from SQLite
        4. Inject Retrieved Context into Structured JSON System Prompt
        5. Generate Local Response via Ollama (Qwen 2.5 1.5B)
        6. Return Structured Reasoning + Evidence Citations + Confidence Rating
```

---

## ⚙️ Setup & Installation Guide

### Prerequisites
1. **Python 3.10+** (Python 3.13 recommended)
2. **Node.js 18+** & **npm**
3. **Ollama**: [Download & Install Ollama](https://ollama.com/)

---

### Step 1: Install & Start Ollama
Launch Ollama and pull the `qwen2.5:1.5b` model:

```bash
# Start Ollama service (if not running as a background service)
ollama serve

# Pull the default local Qwen LLM model
ollama pull qwen2.5:1.5b
```

---

### Step 2: Setup FastAPI Backend

```bash
# Navigate to backend directory
cd backend

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# On Linux / macOS:
source venv/bin/activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create environment configuration file
# On Linux / macOS:
cp .env.example .env
# On Windows (PowerShell):
Copy-Item .env.example .env

# Run FastAPI backend server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend server runs at `http://localhost:8000`. Interactive API documentation is available at `http://localhost:8000/docs`.

---

### Step 3: Setup React Frontend

Open a new terminal window:

```bash
# Navigate to frontend directory
cd frontend

# Install Node modules
npm install

# Create environment configuration file
# On Linux / macOS:
cp .env.example .env
# On Windows (PowerShell):
Copy-Item .env.example .env

# Start Vite dev server
npm run dev
```

The frontend application runs at `http://localhost:5173`.

---

### Step 4: Loading the Sample Dataset
1. Open `http://localhost:5173` in your browser.
2. Go to **Data Sources** or use the Upload section on the Dashboard.
3. Select the provided synthetic sample file: `samples/sample_whatsapp_chat.txt`.
4. The pipeline will automatically transition through: `Uploaded` ➔ `Parsed` ➔ `Stored` ➔ `Indexed` ➔ `AI Ready`.

---

## 🔧 Environment Configuration

### Backend Environment Variables (`backend/.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///./community_intelligence.db` | SQLAlchemy SQLite connection string |
| `CHROMA_DB_DIR` | `./chroma_db` | Storage path for local ChromaDB persistent index |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endpoint for local Ollama service |
| `LLM_MODEL` | `qwen2.5:1.5b` | Ollama model identifier to use for inference |
| `EMBEDDING_MODEL_NAME` | `all-MiniLM-L6-v2` | SentenceTransformer model identifier |
| `DISABLE_SSL_VERIFY` | `false` | **Leave as `false` for normal TLS verification.** Set to `true` only if operating behind corporate proxy environments with custom interception CAs. |
| `PORT` | `8000` | FastAPI server port |
| `HOST` | `0.0.0.0` | FastAPI server host binding |

### Frontend Environment Variables (`frontend/.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `http://localhost:8000/api` | REST API base endpoint for backend server |

---

## 🔒 Privacy & Data Handling

- **Local Processing**: By default, chat processing is performed locally. LLM inference runs through Ollama and embeddings are generated locally using Sentence Transformers; the application does not use a cloud LLM API for these operations.
- **Local Storage**: Uploaded files, parsed SQLite database records, and ChromaDB vector indexes remain strictly on your local filesystem.
- **No Personal Chat Data Committed**: The repository contains only a synthetic demo dataset (`samples/sample_whatsapp_chat.txt`). Real exported personal chats should not be committed to Git.

---

## ⚠️ Limitations & Technical Tradeoffs

- **Format Bounds**: The parser natively targets standard Android (`dd/mm/yyyy, hh:mm - Sender: Message`) and iOS (`[dd/mm/yyyy, hh:mm:ss] Sender: Message`) WhatsApp text exports. Non-standard timestamp formats or custom locale variations may require regex pattern additions.
- **Local Hardware Dependency**: Local LLM inference response times depend on host CPU/GPU hardware. The default model `qwen2.5:1.5b` is selected for low memory consumption and low latency (~1-3s response time on CPU).
- **Retrieval Scope**: Dense vector retrieval surfaces relevant conversation chunks based on semantic similarity. Exact numerical aggregations (e.g. total message counts or member post distributions) are computed deterministically by the SQL analytics service rather than vector search.

---

## 📄 License

Distributed under the [MIT License](LICENSE).
