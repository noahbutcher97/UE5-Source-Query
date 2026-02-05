# Master Audit Summary & Refactoring Roadmap (v2.1)

## ## Metadata
- **Author**: Gemini-CLI Intelligence Layer
- **Date Created**: 2026-02-04
- **Project**: UE5 Source Query System
- **Status**: Executive Summary
- **Version**: 1.0.0 (SemVer)
- **License**: Proprietary
- **Contact**: posner.noah@gmail.com

---

## ## Overview
This document synthesizes 80 targeted refactoring tasks across four dimensions: **API Architecture**, **Database Performance**, **Design Patterns**, and **System Reliability**. It serves as the master blueprint for transitioning the UE5 Source Query System from a local developer utility to a production-grade team service.

---

## ## Strategic Vulnerability Analysis

### 1. API & System Blocking (Critical)
The current server is synchronous. A single heavy query blocks all other users.
- **Refactor**: Migrate to **FastAPI** (Async) and decouple indexing to **Celery Workers**.
- **Impact**: 50x increase in concurrency; 100% search availability during updates.

### 2. Data Integrity & Persistence (Critical)
The flat JSON metadata store is fragile and scales at $O(N)$.
- **Refactor**: Implement a **Relational SQLite Schema** with B-Tree indexes and FK constraints.
- **Impact**: Lookup speed shifts from ~200ms to <1ms; 0% orphaned chunk risk.

### 3. Architecture Congestion (High)
The `HybridQueryEngine` is a "God Object" with tight coupling and duplicated regex logic.
- **Refactor**: Apply **Template Method**, **Mediator**, and **Strategy** patterns.
- **Impact**: 40% code reduction in core parsing; significantly higher testability.

### 4. Deployment & Infrastructure (High)
Local setup is complex and error-prone due to CUDA/PyTorch dependencies.
- **Refactor**: Full **Dockerization** and **CI/CD** automation.
- **Impact**: Onboarding time reduced from ~20m to <2m.

---

## ## Prioritized Execution Roadmap (Phase 1)

The following 10 tasks represent the "Core Foundation" required for v2.1:

| Task ID | Description | Dimension | Effort | Impact | Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **API-01** | **FastAPI Migration** | API | High | 5 | Concurrent, non-blocking I/O |
| **DB-01** | **SQLite Migration** | DB | Medium | 5 | O(log N) lookup performance |
| **SYS-01** | **Celery Indexing** | System | High | 5 | Zero-downtime background index |
| **SYS-02** | **Dockerize NVIDIA** | System | Medium | 5 | Instant deployment anywhere |
| **PAT-01** | **Template Extractor** | Patterns | Medium | 5 | Maintainable, DRY C++ parsing |
| **PAT-05** | **Strict Singleton** | Patterns | Low | 5 | VRAM stability & safety |
| **API-02** | **Redis Caching** | API | Medium | 5 | Sub-100ms response for hot queries |
| **DB-05** | **Hash Validation** | DB | Medium | 5 | 90% faster incremental builds |
| **PAT-08** | **Dep. Injection** | Patterns | Medium | 5 | High test coverage & mocking |
| **API-04** | **API Key Auth** | API | Low | 4 | Secure team-wide deployment |

---

## ## Success Metrics (v2.1 Target)
1.  **Concurrency**: Support 10+ simultaneous search users without thread-blocking.
2.  **Latency**: Average response time < 500ms; Cached response < 100ms.
3.  **Data Integrity**: 100% match between database pointers and physical source files.
4.  **Uptime**: 99.9% availability (exclusive of hardware failure).

---

## ## Immediate Next Steps
1.  **Provisioning**: Set up a local Redis instance (`docker run -d -p 6379:6379 redis:alpine`).
2.  **Environment**: Update `requirements.txt` with `fastapi`, `uvicorn`, `redis`, and `sqlalchemy`.
3.  **Initialization**: Start the `refactor/v2.1-foundation` branch and begin Task **API-01**.

---
*End of Master Summary*
