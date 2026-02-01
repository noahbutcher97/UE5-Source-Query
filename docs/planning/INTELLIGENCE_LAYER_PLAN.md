# Intelligence Layer - Implementation Plan

## Overview
This document outlines the roadmap for integrating advanced AI capabilities into **UE5 Source Query**. The goal is to transform the tool from a "Smart Search Engine" into an "Intelligent Development Assistant" that can explain code, suggest implementations, and reason about Unreal Engine architecture.

## Core Objectives
1.  **Enhance Semantic Understanding**: Move beyond keyword/vector matching to true conceptual understanding via LLM.
2.  **Context-Aware Reasoning**: Answer questions like "How do I use X with Y?" by retrieving definitions for both.
3.  **Multi-Turn Conversation**: Allow refining queries (e.g., "What about for multiplayer?").
4.  **No Regressions**: All new features will live in a dedicated **"Assistant"** tab, keeping the core "Query" tab fast and deterministic.

## Architecture

### 1. Intelligence Service (`ue5_query/services/intelligence.py`)
A standalone service managing the connection to the LLM Provider (Anthropic Claude).
*   **Responsibilities**:
    *   API Key management (via `ConfigManager`).
    *   Prompt construction.
    *   Context window management.
    *   Streaming response handling.

### 2. Context Builder (`ue5_query/core/context_builder.py`)
A bridge between the `HybridQueryEngine` and the `IntelligenceService`.
*   **Responsibilities**:
    *   Takes search results (Definitions, Semantic Hits).
    *   Formats them into an optimized prompt structure (XML/Markdown).
    *   Truncates content intelligently to fit token limits.

### 3. GUI: Assistant Tab (`ue5_query/management/views/assistant_view.py`)
A new dedicated tab in the `UnifiedDashboard`.
*   **Layout**:
    *   **Chat History**: Scrollable conversation view.
    *   **Input Area**: Multi-line text box.
    *   **Context Panel**: Sidebar showing currently attached code snippets.
*   **Features**:
    *   "Include Search Results": Checkbox to automatically run a search and feed results to the LLM.
    *   "Clear History".

## Implementation Roadmap

### Phase 1: Foundation & GUI (Target: Today)
- [ ] Create `IntelligenceService` skeleton.
- [ ] Implement `AssistantView` in the Dashboard.
- [ ] Add API Key configuration validation in the existing Config tab.
- [ ] Verify basic "Hello World" roundtrip to Claude API.

### Phase 2: Retrieval Augmented Generation (RAG)
- [ ] Implement `ContextBuilder`.
- [ ] Connect `HybridQueryEngine` to `AssistantView`.
- [ ] Allow user to "Send to Assistant" from the Query Tab results.

### Phase 3: Advanced Capabilities (Future)
- [ ] **Adaptive Learning**: Cache successful Q&A pairs as synthetic data for vector search.
- [ ] **External Docs**: Integrate scraping of UE5 documentation web pages.
- [ ] **Agentic Capabilities**: Allow the LLM to propose "Search Queries" automatically.

## Directory Structure Changes
```
ue5_query/
├── ai/                  <-- NEW PACKAGE
│   ├── __init__.py
│   ├── service.py       (IntelligenceService)
│   ├── context.py       (ContextBuilder)
│   └── prompts.py       (System Prompts)
├── management/
│   └── views/
│       └── assistant_view.py <-- NEW VIEW
```
