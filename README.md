# 🌐 Community AI Analyst

An enterprise-grade, privacy-first **AI Community Intelligence Platform** designed to analyze community interaction logs (WhatsApp chat exports, with extensible architecture for Discord, Slack, and Google Meet). 

It features **Strategy-Pattern Conversation Chunking**, **ChromaDB Vector Retrieval**, **SQLite Relational Threading**, and **Local Qwen LLM Integration via Ollama** to provide privacy-centric RAG (Retrieval-Augmented Generation), analytical dashboards, automated community intelligence reports, and an interactive Conversation Explorer.

---

## 🌟 Features

- **🔐 100% Privacy & Local Execution**: Runs entirely on local infrastructure powered by Ollama (`qwen2.5:1.5b`) and `sentence-transformers` (`all-MiniLM-L6-v2`). No community chat data ever leaves your machine.
- **💬 Grounded RAG Chat Copilot**: Ask natural language questions grounded strictly in community discussion logs. Produces structured reasoning outputs (`Observation`, `Inference`, `Recommendation`) with confidence rankings and collapsible citation evidence.
- **🧩 Context-Aware Conversation Chunking**: Groups messages dynamically using a Strategy Pattern (`ConversationChunker`) based on time gaps (15 min) and message density constraints, maintaining complete conversational context rather than isolated message fragments.
- **📊 Analytics Dashboard**: Visualizes total members, total messages, top contributors, daily message volume curves, and 24-hour hourly density distributions with visual axis scale indicators and explainer cards.
- **📑 Automated Intelligence Reports**: Synthesizes executive summaries, discussed topics, community sentiment/mood, key trends, active contributors, and strategic recommendations in one click.
- **🔎 Conversation Explorer**: Full-text keyword search, pagination, relative time filters (Last 1h, 24h, 7d, 30d, Custom range), sender filtering, media detection, and streaming export capabilities to `.txt` and `.json`.
- **🎨 Modern SaaS Design**: Notion / Linear / Stripe inspired UI with Light (default) & Dark theme toggling, polished typography (`Inter`), and clean component spacing.

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
  | (Messages & Logs) |         | Store (Embeddings)|          | (Qwen 2.5 LLM)    |
  +-------------------+         +-------------------+          +-------------------+
```

- **Frontend**: React 18, TypeScript, Vite, Lucide Icons, Custom CSS Variable Tokens
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
  ├──► Vector Embedding (Dense 384-d vectors via SentenceTransformers)
  │
  ├──► ChromaDB Indexing (Stores vector embeddings & thread metadata)
  │
  └──► Query Execution Pipeline:
        1. Embed User Query via SentenceTransformers
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
# Start Ollama service (if not running in background)
ollama serve

# Pull local Qwen LLM model
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
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create local environment configuration
cp .env.example .env

# Run FastAPI backend server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend server runs at `http://localhost:8000`. Interactive API documentation is available at `http://localhost:8000/docs`.

---

### Step 3: Setup React Frontend

Open a new terminal window:

```bash
# Navigate to frontend directory
cd frontend

# Install Node modules
npm install

# Copy frontend environment template
cp .env.example .env

# Start Vite dev server
npm run dev
```

Frontend application runs at `http://localhost:5173`.

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

## 🔒 Privacy & Data Protection

- **Local Inference**: All LLM queries are executed via your local Ollama daemon. No chat messages or prompts are sent to cloud LLM APIs.
- **Local Embeddings**: SentenceTransformer embeddings are generated locally on host CPU/GPU.
- **Local Storage**: Uploaded WhatsApp files, parsed SQLite records, and ChromaDB vector stores remain strictly on your local filesystem.
- **No Real Chat Data Committed**: The repository contains only synthetic demo data (`samples/sample_whatsapp_chat.txt`). Real exported personal chats should never be committed.

---

## ⚠️ Limitations & Technical Tradeoffs

- **Format Bounds**: Parser natively targets standard Android (`dd/mm/yyyy, hh:mm - Sender: Message`) and iOS (`[dd/mm/yyyy, hh:mm:ss] Sender: Message`) WhatsApp text exports. Non-standard custom locale timestamps may require pattern additions.
- **Hardware Requirements**: Local LLM inference speed depends on host CPU/GPU capability. For low-spec machines, `qwen2.5:1.5b` offers optimal response latency (~1-3 seconds).
- **Retrieval Scope**: Dense vector retrieval matches thread semantic relevance. Queries asking for exact statistical counts (e.g. "How many total messages were sent on Tuesday?") rely on the Analytics Dashboard engine rather than vector search.

---

## 📄 License

Distributed under the [MIT License](LICENSE).
