# Active Project Plan: v2.1 Infrastructure & Production Readiness

**Date**: February 4, 2026
**Current Status**: v2.0.0-rc (Phases 1-5 Complete)
**Objective**: Transition from a local developer utility to a production-grade asynchronous service.

---

## 1. Roadmap Overview

The system is currently stable but architecturally monolithic. The v2.1 cycle focuses on **Async I/O**, **Relational Data Integrity**, and **Background Task Management**.

### Key Deliverables:
1.  **FastAPI Migration**: Replace `http.server` with an asynchronous ASGI layer.
2.  **SQLite Migration**: Transition from flat JSON metadata to a relational model with B-Tree indexing.
3.  **Redis Caching**: Implement semantic result caching to reduce GPU load by 70-90%.
4.  **Celery/Worker Decoupling**: Move indexing to background workers to enable zero-downtime search.

---

## 2. Prioritized Task List (Top 10)

Refer to `docs/user/audits/Audit_Summary_2026-02-04.md` for the full 80-item backlog.

| ID | Task | Effort | Impact | Status |
| :--- | :--- | :--- | :--- | :--- |
| **API-01** | **FastAPI Migration** | High | 5 | 🚀 Next |
| **DB-01** | **SQLite Migration** | Medium | 5 | 🚀 Next |
| **SYS-01** | **Celery Indexing** | High | 5 | ⏸️ Planned |
| **SYS-02** | **Dockerize NVIDIA** | Medium | 5 | ⏸️ Planned |
| **PAT-01** | **Template Extractor** | Medium | 5 | ⏸️ Planned |
| **API-02** | **Redis Caching** | Medium | 5 | ⏸️ Planned |
| **DB-05** | **Hash Validation** | Medium | 5 | ⏸️ Planned |
| **PAT-08** | **Dep. Injection** | Medium | 5 | ⏸️ Planned |
| **API-04** | **API Key Auth** | Low | 4 | ⏸️ Planned |
| **SYS-16** | **VRAM Isolation** | High | 5 | ⏸️ Planned |

---

## 3. Implementation Workflow

### Phase A: The "Async" Foundation
-   **T-001**: Install `fastapi`, `uvicorn`, and `pydantic`.
-   **T-002**: Create `ue5_query/server/app.py` and implement the basic search endpoint.
-   **T-003**: Implement `X-API-Key` middleware.

### Phase B: Relational Data Layer
-   **T-004**: Define `data/schema.sql` for the new SQLite model.
-   **T-005**: Write migration script `tools/migrate_json_to_db.py`.
-   **T-006**: Update `HybridQueryEngine` to prefer SQLite for metadata filtering.

### Phase C: Infrastructure & Scaling
-   **T-007**: Provision local Redis for result caching.
-   **T-008**: Implement Celery worker for incremental indexing.
-   **T-009**: Create `Dockerfile` with NVIDIA-runtime support.

---

## 4. Success Metrics
-   **Concurrency**: 50+ simultaneous search users without thread-blocking.
-   **Latency**: <100ms for cached queries; <500ms for fresh filtered searches.
-   **Integrity**: 0% chance of "orphaned chunks" via Foreign Key constraints.
-   **Deployment**: One-command setup via `docker-compose up`.

---

## 5. Reference Audits
Detailed analysis for each dimension can be found in `docs/user/audits/`:
-   `Audit_API_2026-02-04.md`
-   `Audit_Database_2026-02-04.md`
-   `Audit_Patterns_2026-02-04.md`
-   `Audit_System_2026-02-04.md`
-   `Audit_Summary_2026-02-04.md`
