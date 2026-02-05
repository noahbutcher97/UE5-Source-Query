# UE5 Source Query 🚀

**Intelligent Semantic Search for Unreal Engine 5 Source Code.**

UE5 Source Query is a hybrid search platform that combines regex-based definition extraction with semantic vector search (RAG). It helps developers and AI agents navigate the massive UE5 codebase instantly.

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.11-green)
![UE5](https://img.shields.io/badge/UE-5.3%2B-orange)
![GPU](https://img.shields.io/badge/GPU-RTX%203090%2F4090%2F5090-purple)

---

## 🔥 Key Features

*   **Hybrid Search:** Combines exact C++ definition lookup (`UCLASS`, `FStruct`, `Enum`) with conceptual semantic search.
*   **Zero-Latency:** Queries run in milliseconds using optimized vector indices (FAISS/NumPy mmap).
*   **Dual Scope:** Index both the **Unreal Engine** source and your **Game Project** source simultaneously.
*   **Multi-Modal:** Supports C++, Headers, Blueprints (future), and Documentation (`.md`, `.pdf`, `.docx`).
*   **AI-Native:** Designed for integration with AI Agents (Cursor, Claude, Gemini) via structured JSON APIs.

## 📚 Documentation

| Guide | Audience | Description |
| :--- | :--- | :--- |
| **[User Guide](docs/user/getting_started.md)** | Developers | How to use the GUI Dashboard, configure paths, and run queries. |
| **[AI Agent Guide](docs/user/ai_integration.md)** | AI Bots | Protocol for Cursor/Claude/Gemini integration (JSON schemas, exit codes). |
| **[API Reference](docs/dev/api_reference.md)** | Engineers | Python API docs for extending the tool or building plugins. |
| **[Team Setup](docs/deployment/team_setup.md)** | Leads | Deploying shared indices and configuration for teams. |

---

## ⚡ Quick Start

### 1. Installation
Run the automated installer to set up the Python environment and dependencies.

**Windows:**
```batch
Setup.bat
```

**Linux/Mac:**
```bash
./setup.sh
```

### 2. Launch Dashboard
Open the GUI to configure your Engine path and build the search index.

**Windows:**
```batch
launcher.bat
```

**Linux/Mac:**
```bash
./launcher.sh
```

### 3. CLI Usage
Once indexed, you can query from the terminal:

```bash
# Natural Language
ask.bat "how does character movement slide"

# Definition Lookup (Code Only)
ask.bat "FHitResult" --format code

# Interactive Mode (REPL)
ask.bat -i
```

---

## 🤖 For AI Agents

This tool follows the **Model Context Protocol (MCP)** principles for tool introspection.

**Self-Description:**
```bash
ask.bat --describe
```

**Environment Context:**
```bash
python -m ue5_query.utils.agent_introspect
```

**Structured Output:**
```bash
ask.bat "query" --format json
```

See **[docs/user/ai_integration.md](docs/user/ai_integration.md)** for full integration details.

---

## 🏗 Architecture

The system consists of three layers:
1.  **Indexing Layer:** Scans source files, chunks text, generates embeddings (UnixCoder), and builds metadata.
2.  **Query Layer:** `HybridQueryEngine` routes queries between Regex Extractor and Vector Search (Filtered/Boosted).
3.  **Interface Layer:**
    *   **CLI:** `ask.bat` for terminal/agent use.
    *   **GUI:** `launcher.bat` for configuration and management.
    *   **Server:** `ue5_query/server/retrieval_server.py` for persistent HTTP access.

## 🤝 Contributing

We welcome contributions! Please see **[docs/dev/architecture.md](docs/dev/architecture.md)** for architectural decision records (ADRs) and coding standards.