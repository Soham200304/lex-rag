# LexRAG — Multi-Document Legal & Research Assistant
## Comprehensive Project Prompt

---

## Project Idea

LexRAG is an AI-powered mobile and backend platform that allows lawyers, researchers, paralegals, and students to upload multiple legal or research documents (contracts, NDAs, case files, research papers, legislation) and interrogate them using natural language. Instead of manually reading through hundreds of pages, a user types a question like *"Does the liability clause in the service agreement conflict with clause 7 of the NDA?"* and receives a precise, cited answer synthesised from across all uploaded documents — streamed in real time, token by token, with clickable source citations linking back to the exact page and section of the original PDF.

The system is not a simple keyword search or a chatbot with a document pasted into its context. It is a full Retrieval-Augmented Generation (RAG) pipeline with an agentic query loop: the system decomposes complex questions into sub-queries, retrieves evidence from a hybrid search engine (semantic + keyword), re-ranks results with a cross-encoder model, synthesises a reasoned answer with inline citations, and self-evaluates confidence — re-querying with a refined question if the retrieved evidence is insufficient.

---

## Problem Statement

Legal and research professionals face a critical information retrieval problem:

1. **Volume overload.** A single legal matter can involve dozens of contracts, exhibits, amendments, and precedents — often thousands of pages. Reading them all before answering a question is impractical.

2. **Cross-document reasoning.** The most important questions in legal work span multiple documents. Standard search tools (Ctrl+F, keyword search) can only search one document at a time and cannot reason across them.

3. **Citation requirements.** Legal answers must be traceable. A conclusion without a source is worthless in professional or academic contexts. Generic AI chatbots hallucinate citations or provide no traceability.

4. **Confidentiality.** Legal documents cannot be uploaded to public AI tools. The system must be self-hostable, with strict per-user data isolation — one user must never be able to query another user's documents.

5. **Real-time feedback.** Waiting 30–60 seconds for a complete response breaks workflow. Professionals need answers to stream progressively, the way a colleague would speak — thinking out loud and building the answer incrementally.

---

## Solution

LexRAG solves these problems with a three-layer architecture:

**Layer 1 — Ingestion pipeline.** Uploaded PDFs are parsed, chunked by semantic structure (headings, clauses, sections), embedded into dense vector representations, and indexed in a hybrid search engine combining ChromaDB (semantic) and BM25 (keyword). Every chunk retains its document ID, page number, and section title as metadata. Ingestion runs asynchronously in a background worker queue so the API never blocks.

**Layer 2 — Agentic RAG query engine.** Complex questions are decomposed into 2–4 targeted sub-queries by an LLM planner. Each sub-query runs through the hybrid retriever, which fuses semantic and keyword scores using Reciprocal Rank Fusion, then re-ranks the top-20 results to top-5 using a cross-encoder model. A confidence gate checks whether the retrieved evidence is sufficient — if not, the agent refines and re-queries autonomously. The final synthesis LLM call produces a cited answer where every claim maps to [document title, page number]. The answer streams token by token via Server-Sent Events.

**Layer 3 — Flutter mobile app.** A cross-platform mobile app handles authentication, document management (upload, list, delete with ingestion progress tracking), and the query interface. Answers stream character by character into a Markdown renderer. Citation markers in the text render as tappable chips that link to the source document at the exact page. BLoC manages the query lifecycle state machine; Riverpod manages shared reactive state (auth session, document list).

---

## Goals and Non-Goals

**Goals:**
- Multi-document natural language Q&A with inline citations
- Real-time streaming responses via SSE
- Per-user document isolation with JWT authentication
- Async ingestion pipeline that never blocks the API
- Hybrid retrieval (semantic + keyword) with cross-encoder re-ranking
- Agentic re-query loop for confidence-gated answers
- Flutter mobile app with BLoC + Riverpod state management
- Redis caching for repeated queries
- Rate limiting and background task queue for production readiness

**Non-Goals (explicitly out of scope for v1):**
- Multi-language document support
- Real-time collaboration between users
- Document editing or annotation
- Integration with external legal databases (Westlaw, LexisNexis)
- Fine-tuned domain-specific LLM (uses OpenAI API)

---

## Technical Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    Flutter Mobile App                    │
│   AuthNotifier (Riverpod) │ DocumentListProvider        │
│   QueryBloc (BLoC)        │ SSE streaming widget        │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTPS + SSE
┌─────────────────────▼───────────────────────────────────┐
│                   FastAPI Backend                        │
│   /auth/register  /auth/token                           │
│   /documents      (upload, list, delete, status)        │
│   /query          (SSE streaming endpoint)              │
│   JWT middleware  │ Rate limiting (slowapi)             │
│   Redis cache     │ Dependency injection                │
└──────┬────────────────────────────┬─────────────────────┘
       │ SQLAlchemy async           │ ARQ job queue
┌──────▼──────────┐        ┌────────▼────────────────────┐
│   PostgreSQL    │        │     ARQ Worker Process       │
│   users table   │        │     PDF parse (PyMuPDF)      │
│   documents     │        │     Semantic chunking        │
│   table         │        │     OpenAI embeddings        │
│   (metadata +   │        │     ChromaDB storage         │
│   job status)   │        │     BM25 index build         │
└─────────────────┘        └─────────────────────────────┘
                                      │
              ┌───────────────────────▼──────────────────┐
              │              RAG Query Engine             │
              │   Query planner (sub-query decomposition) │
              │   Hybrid retriever (BM25 + ChromaDB RRF)  │
              │   Cross-encoder re-ranker                 │
              │   Confidence gate + re-query loop         │
              │   Citation-aware synthesis (OpenAI GPT-4) │
              └──────────────────────────────────────────┘
```

### Data Flow — Document Ingestion

```
User uploads PDF
      │
      ▼
POST /documents/upload
  → save file to disk
  → insert Document row (status: pending)
  → enqueue ARQ ingestion job
  → return document_id immediately
      │
      ▼
ARQ Worker picks up job
  → update status: processing
  → PyMuPDF extracts text + page numbers + headings
  → Semantic chunker splits on heading boundaries
    (fallback: recursive character splitter, 512 tokens, 50 overlap)
  → Each chunk tagged: {doc_id, page_num, section_title, user_id}
  → OpenAI text-embedding-3-small → 1536-dim vector per chunk
  → ChromaDB stores vector + metadata
  → BM25 index rebuilt over user's full corpus
  → update status: done (or failed + error_message)
      │
      ▼
Flutter polls GET /documents/{id}/status every 3s
  → shows progress indicator
  → updates to "ready to query" when done
```

### Data Flow — Query

```
User types question, selects documents
      │
      ▼
POST /query {query, document_ids}
  → check Redis cache (key: SHA256(query + sorted_doc_ids + user_id))
  → cache hit → stream cached response immediately
  → cache miss → enter agent loop:
      │
      ▼
Query Planner (GPT-4)
  → decomposes question into 2–4 sub-queries
  → e.g. "Does liability clause conflict with NDA cap?"
    becomes:
    1. "liability clause scope service agreement"
    2. "liability cap amount NDA"
    3. "indemnification exclusions both documents"
      │
      ▼
For each sub-query → Hybrid Retriever:
  → BM25 keyword search (top-20 chunks)
  → ChromaDB semantic search (top-20 chunks)
  → Reciprocal Rank Fusion → unified ranked list
  → Cross-encoder re-ranker → top-5 chunks
  → Filter: only chunks where user_id matches
      │
      ▼
Confidence Gate:
  → if top chunk score < 0.4 → refine query + retry (max 2 retries)
  → if sufficient evidence → proceed to synthesis
      │
      ▼
Synthesis (GPT-4):
  → prompt includes all retrieved chunks with metadata
  → instructed to cite inline: [Document Title, p.14]
  → streams response via FastAPI StreamingResponse
  → sends "data: [DONE]" sentinel at end
      │
      ▼
Flutter QueryBloc receives SSE stream:
  → QueryStreaming state accumulates tokens
  → MarkdownBody renders progressively
  → [Doc, p.N] markers parsed → ActionChip citations
  → QueryComplete state shows citation chips
      │
      ▼
Store in Redis cache with 1-hour TTL
```

---

## Tech Stack

### Backend

| Concern | Technology | Reason |
|---|---|---|
| API framework | FastAPI 0.111 | Async-native, automatic OpenAPI docs, best dependency injection system in Python |
| Language | Python 3.11 | asyncio maturity, ML ecosystem |
| Database ORM | SQLAlchemy 2.0 async | Modern `mapped_column()` API, full async support, Alembic integration |
| DB driver | asyncpg | Only production-grade async Postgres driver |
| Database | PostgreSQL 16 | ACID compliance, UUID support, reliable |
| Migrations | Alembic | Only tool that integrates cleanly with SQLAlchemy |
| Validation | Pydantic v2 | Built into FastAPI, 5–50x faster than v1 |
| Auth | python-jose + passlib[bcrypt] | JWT encode/decode + secure password hashing |
| PDF parsing | PyMuPDF (fitz) | Fastest parser, preserves layout, page numbers, headings |
| Embeddings | OpenAI text-embedding-3-small | Cost-efficient (0.02$/1M tokens), 1536-dim, strong multilingual |
| Vector store | ChromaDB | No separate process needed for local dev, simple Python API |
| Keyword search | rank-bm25 | Lightweight, pure Python BM25 implementation |
| Re-ranking | sentence-transformers | Cross-encoder/ms-marco-MiniLM-L-6-v2 runs locally, no API cost |
| LLM synthesis | OpenAI GPT-4o | Best instruction-following for citation-constrained prompts |
| Task queue | ARQ | Async-native worker queue built on Redis, fits FastAPI's event loop |
| Cache | Redis 7 | Sub-millisecond reads, TTL support, used by both ARQ and query cache |
| Rate limiting | slowapi | FastAPI-native, per-user rate limiting middleware |
| Containerisation | Docker + Docker Compose | Reproducible local environment, one command to start all services |

### Flutter (Mobile)

| Concern | Technology | Reason |
|---|---|---|
| Framework | Flutter 3.x | Single codebase for iOS + Android |
| Language | Dart | Strongly typed, async-first, excellent tooling |
| Event-driven state | flutter_bloc | Query lifecycle: discrete events → predictable states |
| Reactive state | Riverpod | Auth session, document list: reactive data shared across widgets |
| HTTP client | dio | Streaming response support for SSE, interceptors for JWT injection |
| Navigation | go_router | Declarative routing, deep link support |
| Secure storage | flutter_secure_storage | Keychain/Keystore-backed JWT persistence |
| File picking | file_picker | Cross-platform PDF selection |
| Markdown render | flutter_markdown | Renders streamed answer with formatting intact |

### Infrastructure

| Concern | Technology |
|---|---|
| Local dev | Docker Compose (Postgres + Redis + backend + worker) |
| Environment config | pydantic-settings loading `.env` |
| Secrets management | `.env` file (never committed), `.env.example` committed |

---

## Project Structure

```
legal-rag/
├── backend/
│   ├── alembic/
│   │   ├── versions/
│   │   └── env.py                  # async-patched Alembic env
│   ├── core/
│   │   ├── config.py               # pydantic-settings: loads .env
│   │   └── database.py             # async engine + session factory + Base
│   ├── models/
│   │   ├── base.py                 # TimestampMixin (created_at, updated_at)
│   │   ├── user.py                 # User model — UUID PK, email, hashed_password
│   │   └── document.py             # Document model — IngestionStatus enum, owner FK
│   ├── schemas/
│   │   ├── user.py                 # UserCreate, UserResponse (Pydantic)
│   │   └── document.py             # DocumentCreate, DocumentResponse
│   ├── routers/
│   │   ├── auth.py                 # POST /auth/register, POST /auth/token
│   │   ├── documents.py            # CRUD + upload + status polling
│   │   └── query.py                # POST /query → StreamingResponse SSE
│   ├── dependencies/
│   │   ├── auth.py                 # get_current_user (JWT → User)
│   │   └── database.py             # get_db (AsyncSession yield)
│   ├── services/
│   │   ├── ingestion.py            # PDF parse → chunk → embed → ChromaDB
│   │   └── rag.py                  # hybrid retrieval + re-rank + agent loop
│   ├── workers/
│   │   └── tasks.py                # ARQ WorkerSettings + ingestion task
│   ├── main.py                     # FastAPI app + lifespan + CORS
│   ├── alembic.ini
│   ├── requirements.txt
│   └── Dockerfile
├── flutter/
│   └── lib/
│       ├── core/
│       │   ├── api/
│       │   │   └── api_client.dart # dio instance + JWT interceptor
│       │   └── storage/
│       │       └── secure_storage.dart
│       ├── features/
│       │   ├── auth/
│       │   │   ├── notifier/
│       │   │   │   └── auth_notifier.dart     # Riverpod: login/logout/token
│       │   │   └── screens/
│       │   │       └── login_screen.dart
│       │   ├── documents/
│       │   │   ├── providers/
│       │   │   │   └── document_list_provider.dart  # Riverpod: doc list
│       │   │   └── screens/
│       │   │       └── document_list_screen.dart
│       │   └── query/
│       │       ├── bloc/
│       │       │   ├── query_bloc.dart
│       │       │   ├── query_event.dart
│       │       │   └── query_state.dart
│       │       └── screens/
│       │           └── query_screen.dart
│       └── main.dart
├── .env
├── .env.example
├── .gitignore
└── docker-compose.yml
```

---

## Database Schema

### `users` table
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK, default uuid4 |
| email | VARCHAR(255) | UNIQUE, NOT NULL, indexed |
| hashed_password | VARCHAR(255) | NOT NULL |
| full_name | VARCHAR(255) | NOT NULL |
| is_active | BOOLEAN | NOT NULL, default true |
| is_admin | BOOLEAN | NOT NULL, default false |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

### `documents` table
| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK, default uuid4 |
| owner_id | UUID | FK → users.id CASCADE, NOT NULL, indexed |
| title | VARCHAR(500) | NOT NULL |
| filename | VARCHAR(500) | NOT NULL |
| file_path | VARCHAR(1000) | NOT NULL |
| file_size_bytes | INTEGER | NOT NULL |
| page_count | INTEGER | NULLABLE (set post-ingestion) |
| ingestion_status | VARCHAR(20) | NOT NULL, indexed: pending/processing/done/failed |
| error_message | TEXT | NULLABLE |
| chunk_count | INTEGER | NULLABLE (set post-ingestion) |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

---

## API Endpoints

### Auth
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /auth/register | None | Create new user account |
| POST | /auth/token | None | Login → returns JWT access token |

### Documents
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /documents/upload | JWT | Upload PDF → queues ingestion job |
| GET | /documents | JWT | List current user's documents |
| GET | /documents/{id} | JWT | Get single document (ownership checked) |
| GET | /documents/{id}/status | JWT | Poll ingestion status |
| DELETE | /documents/{id} | JWT | Delete document + ChromaDB chunks |

### Query
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /query | JWT | SSE stream: agent loop → cited answer |

---

## Key Implementation Patterns

### Dependency Injection Chain
```
Request
  └── get_db()                    yields AsyncSession
  └── get_current_user()          Depends(get_db) → validates JWT → returns User
  └── get_document_access()       Depends(get_current_user) + Depends(get_db)
                                  → checks ownership → returns Document
  └── require_admin()             Depends(get_current_user) → checks is_admin
```

### BLoC State Machine (QueryBloc)
```
Events:          QuerySubmitted | QueryCancelled | QueryRetried
States:          QueryIdle → QueryLoading → QueryStreaming → QueryComplete
                                                          ↘ QueryError
Key patterns:
  - emit.forEach() over SSE stream (not raw await for — handles cancellation)
  - buildWhen on input bar (prevents rebuild on every token)
  - CancelToken passed to dio for mid-stream cancellation
  - QueryStreaming.copyWithToken() accumulates text immutably
```

### Chunking Strategy
```
Priority 1: Split on heading boundaries (##, clause numbers, section titles)
Priority 2: Recursive character splitter (512 tokens, 50 token overlap)
Metadata per chunk: {doc_id, page_num, section_title, user_id, chunk_index}
Rationale: Legal docs have strong structural signals. Heading-aware chunks
           keep clauses intact — critical for accurate citation.
```

### Hybrid Retrieval + RRF
```python
# Reciprocal Rank Fusion formula
rrf_score(chunk) = Σ 1 / (k + rank_in_list)
# k=60 (standard), summed across BM25 rank and ChromaDB rank
# Combines keyword precision with semantic understanding
# Cross-encoder then re-scores top-20 unified results → top-5
```

### Redis Caching
```
cache_key = SHA256(query.lower().strip() + "|" + "|".join(sorted(doc_ids)) + "|" + user_id)
TTL = 3600 seconds (1 hour)
On hit: stream cached response bytes directly, skip LLM entirely
On miss: run full agent loop, store result, stream to client
```

---

## Week-by-Week Implementation Plan

| Week | Phase | Deliverable |
|---|---|---|
| 1 | Backend foundation | User + Document models, Alembic migration, JWT auth endpoints working in /docs |
| 2 | Document CRUD | Upload endpoint, ownership-protected list/delete, ingestion_status field |
| 3 | Ingestion pipeline | PDF → chunks → embeddings → ChromaDB via ARQ worker |
| 4 | Hybrid retrieval | BM25 + ChromaDB RRF + cross-encoder re-ranker, user-scoped results |
| 5 | Agent loop + SSE | Query planner, confidence gate, synthesis streaming, [DONE] sentinel |
| 6 | Flutter auth + docs | AuthNotifier, DocumentListProvider, login screen, upload with progress |
| 7 | Flutter query UI | QueryBloc, SSE consumption, streaming Markdown, citation chips |
| 8 | Production hardening | Redis cache, rate limiting, system design review, failure mode analysis |

---

## Environment Variables

```bash
# Database
POSTGRES_USER=legalrag
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=legalrag
DATABASE_URL=postgresql+asyncpg://legalrag:<password>@postgres:5432/legalrag

# Redis
REDIS_URL=redis://redis:6379

# JWT
JWT_SECRET_KEY=<256-bit-random-string>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# OpenAI
OPENAI_API_KEY=sk-...

# App
UPLOAD_DIR=/app/uploads
DEBUG=true
```

---

## Design Decisions and Rationale

**UUID primary keys over auto-increment integers.**
Auto-increment IDs leak row counts to clients and are guessable in URLs. UUIDs are opaque, safe to expose, and can be generated before the DB insert — useful for optimistic UI updates in Flutter.

**asyncpg over psycopg2.**
psycopg2 is synchronous and blocks the event loop. asyncpg is the only production-grade async Postgres driver and is required for SQLAlchemy 2.0 async to work correctly.

**`lazy="selectin"` on all relationships.**
SQLAlchemy's default lazy loading fires a new SQL query when you access a relationship attribute. In sync code this is invisible. In async code it attempts a DB call outside an async context and raises `MissingGreenlet`. `selectin` loads relationships with a batched `WHERE id IN (...)` query at fetch time — safe, predictable, and N+1-efficient.

**ARQ over Celery for background tasks.**
Celery is the industry standard but was designed for sync Python. ARQ is built from the ground up for asyncio — tasks are `async def` functions, it shares FastAPI's event loop model, and setup is dramatically simpler (no separate broker config, no serialisation format choices).

**Hybrid search over pure vector search.**
Semantic search misses exact legal terms: clause numbers, defined terms, case citations. A search for "Section 14(b)" will score poorly on cosine similarity but perfectly on BM25. Combining both via RRF captures precision (BM25) and conceptual understanding (dense) — consistently outperforms either alone by 15–25% on legal retrieval benchmarks.

**Cross-encoder re-ranking over bi-encoder scoring.**
Bi-encoders (the embedding model) score query and document independently — fast but imprecise. A cross-encoder takes the query and each candidate chunk together as a pair and computes a joint relevance score — much more accurate but too slow to run on the full corpus. Running it only on the top-20 retrieved chunks gives the accuracy benefit at acceptable latency.

**BLoC for query lifecycle, Riverpod for shared state.**
The query flow is inherently event-driven with a strict linear state sequence (Idle → Loading → Streaming → Complete). BLoC's explicit event/state model makes this flow auditable and testable. The document list and auth session are reactive data that many widgets observe simultaneously with no complex sequencing — Riverpod's provider model handles this more naturally than BLoC would.

---

## Security Considerations

- Passwords hashed with bcrypt (cost factor 12) via passlib — never stored plain
- JWT tokens expire after 30 minutes; refresh token pattern for longer sessions
- Every document query filters by `user_id` at the DB and ChromaDB layer — data isolation is enforced at retrieval time, not just at the API layer
- File uploads validated for MIME type and size before storage
- Rate limiting on `/query` (10 req/min per user) prevents LLM cost abuse
- `.env` never committed; `.env.example` documents required keys
- CORS origins locked down in production (wildcard only in dev)
- `/docs` (Swagger UI) disabled when `DEBUG=false`

---

## Local Development — Quick Start

```bash
# 1. Clone and enter project
git clone <repo> && cd legal-rag

# 2. Copy env template
cp .env.example .env
# Fill in POSTGRES_PASSWORD, JWT_SECRET_KEY, OPENAI_API_KEY

# 3. Start infrastructure
docker compose up postgres redis -d

# 4. Set up Python environment
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 5. Run database migrations
alembic upgrade head

# 6. Start the full stack
docker compose up --build

# 7. Verify
curl http://localhost:8000/health   # → {"status": "ok"}
open http://localhost:8000/docs     # Interactive API explorer

# 8. Flutter
cd ../flutter
flutter pub get
flutter run
```

---

*LexRAG — built to learn FastAPI async patterns, production RAG pipelines,
agentic AI loops, Flutter BLoC/Riverpod state management, and real-world
system design in a single cohesive project.*
