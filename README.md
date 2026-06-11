# X-Ray-SYSTEM 

**NFD** là hệ thống quản lý tri thức doanh nghiệp được hỗ trợ bởi AI, kết hợp tìm kiếm lai (Hybrid Search), các tác nhân AI hội thoại (Deep Agent), và pipeline xử lý tài liệu thông minh. Hệ thống cho phép cá nhân và đội nhóm xây dựng kho kiến thức riêng từ nhiều nguồn dữ liệu khác nhau, sau đó truy vấn qua giao diện chat thời gian thực. Đây là giải pháp mã nguồn mở thay thế cho NotebookLM, Perplexity và Glean.

---

## Mục lục

- [Tổng quan hệ thống](#tổng-quan-hệ-thống)
- [Tính năng chính](#tính-năng-chính)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
- [Hướng dẫn cài đặt & khởi chạy](#hướng-dẫn-cài-đặt--khởi-chạy)
  - [1. Khởi chạy cơ sở hạ tầng (Docker)](#1-khởi-chạy-cơ-sở-hạ-tầng-docker)
  - [2. Backend (FastAPI)](#2-backend-fastapi)
  - [3. Frontend (Next.js)](#3-frontend-nextjs)
  - [4. Browser Extension (Plasmo)](#4-browser-extension-plasmo)
  - [5. Triển khai Production](#5-triển-khai-production)
- [Biến môi trường](#biến-môi-trường)
- [API Endpoints](#api-endpoints)
- [Luồng xử lý dữ liệu](#luồng-xử-lý-dữ-liệu)
- [Hybrid RAG Pipeline](#hybrid-rag-pipeline)
- [CI/CD & Versioning](#cicd--versioning)
- [Tài liệu tham khảo](#tài-liệu-tham-khảo)

---

## Tổng quan hệ thống

X-Ray-SYSTEM là một nền tảng RAG (Retrieval-Augmented Generation) toàn diện với các khả năng:

- **Xử lý tài liệu thông minh:** Parse, chunk, embed tài liệu tự động với Docling
- **Tìm kiếm lai (Hybrid Search):** Kết hợp tìm kiếm ngữ nghĩa (dense) và từ khóa (sparse) với RRF ranking
- **Chat AI hội thoại:** Tác nhân LangGraph với khả năng sử dụng tools, trích dẫn nguồn, streaming thời gian thực
- **Không gian làm việc đa thuê (Multi-tenant):** Search Spaces với RBAC (Owner / Editor / Viewer)
- **Hỗ trợ đa LLM:** Kết nối bất kỳ nhà cung cấp LLM nào qua LiteLLM (OpenAI, Anthropic, Google, Azure, v.v.)

---

## Tính năng chính

| Tính năng | Mô tả |
|---|---|
| **Document Ingestion** | Upload PDF, DOCX, TXT, MD, HTML, |
| **Connector Sync** | Đồng bộ tự động từ Google Drive |
| **Hybrid Search** | Dense (pgvector cosine similarity) + Sparse (full-text search) + RRF fusion |
| **Deep Agent Chat** | LangGraph-based agent với tool use: knowledge_base, web search, MCP, report generation |
| **Real-time Streaming** | SSE (Server-Sent Events) theo chuẩn Vercel AI SDK protocol |
| **Multi-tenant Workspaces** | Search Spaces độc lập; RBAC với vai trò Owner, Editor, Viewer |
| **Source Citation** | Trích dẫn chunk nguồn chính xác trong từng câu trả lời |
| **Async Processing** | Celery workers xử lý nền: parse, chunk, embed, sync, notification, cleanup |
| **Browser Extension** | Plasmo MV3 extension — lưu trang web (kể cả trang cần đăng nhập) vào kho kiến thức |
| **LLM Agnostic** | LiteLLM tích hợp 20+ nhà cung cấp LLM và embedding model |
| **RBAC** | Phân quyền chi tiết; mời thành viên vào workspace qua email |
| **Notes** | Tạo ghi chú markdown gắn với chat thread |

---

## Kiến trúc hệ thống

```mermaid
graph TD
    %% Client Layer
    Web["nbd_web\n(Next.js 16 / React 19)"]
    Ext["nbd_browser_extension\n(Plasmo MV3)"]

    %% API Layer
    Backend["nbd_backend\n(FastAPI / Python 3.12)"]

    %% Async Processing
    Broker[("Redis\n(Broker & Cache)")]
    Worker["Celery Worker / Beat\n(Background Tasks)"]

    %% AI Layer
    LiteLLM["LiteLLM\n(LLM Router)"]
    DeepAgent["Deep Agent\n(LangGraph)"]

    %% Storage Layer
    Postgres[("PostgreSQL 16\n+ pgvector")]
    ElectricSQL["ElectricSQL\n(Realtime Sync)"]

    %% Connections
    Ext -->|"Lưu trang web / Gửi API"| Backend
    Web -->|"REST API / SSE Stream"| Backend
    Backend -->|"CRUD & Vector Embeddings"| Postgres
    Backend -->|"Enqueue Tasks"| Broker
    Broker -->|"Fetch Tasks"| Worker
    Worker -->|"Process & Index"| Postgres
    Worker -->|"LLM Calls"| LiteLLM
    Backend -->|"Chat Query"| DeepAgent
    DeepAgent -->|"Hybrid Search / Tools"| Backend
    DeepAgent -->|"LLM Inference"| LiteLLM
    Web <-->|"Sync trạng thái UI"| ElectricSQL
    ElectricSQL <--> Postgres
```

### Các thành phần

| Thành phần | Mô tả |
|---|---|
| **`nbd_web`** | Giao diện web Next.js 16 (App Router), Tailwind CSS 4, Plate.js editor, Jotai state, TanStack Query, i18n, PostHog analytics |
| **`nbd_backend`** | FastAPI Python 3.12: Auth (JWT/OAuth), RBAC, Deep Agent (LangGraph), Hybrid Search, Streaming SSE, indexing pipeline |
| **Celery Worker** | Xử lý bất đồng bộ: parse tài liệu (Docling/Unstructured/LlamaCloud), chunk (Chonkie), embed (LiteLLM), sync connectors, cleanup |
| **`nbd_browser_extension`** | Plasmo MV3 React extension — chuyển đổi HTML sang semantic markdown, gửi lên backend để index |
| **PostgreSQL + pgvector** | Lưu trữ tất cả dữ liệu; pgvector cho vector embeddings và cosine similarity search |
| **Redis** | Celery broker, result backend, rate limiting (SlowAPI), cache |
| **ElectricSQL** | Đồng bộ trạng thái UI thời gian thực (optional) |

---

## Cấu trúc dự án

```
X-Ray-SYSTEM/
├── nbd_backend/                    # FastAPI backend (Python 3.12)
│   ├── app/
│   │   ├── agents/
│   │   │   └── new_chat/          # Deep Agent Framework (LangGraph)
│   │   │       ├── chat_deepagent.py
│   │   │       ├── checkpointer.py
│   │   │       ├── llm_config.py
│   │   │       └── tools/         # Tool registry (knowledge_base, search, MCP, v.v.)
│   │   ├── indexing_pipeline/     # Document processing pipeline
│   │   │   ├── indexing_pipeline_service.py
│   │   │   ├── document_chunker.py
│   │   │   ├── document_embedder.py
│   │   │   ├── document_summarizer.py
│   │   │   └── document_persistence.py
│   │   ├── retriever/             # Hybrid search engines
│   │   │   ├── chunks_hybrid_search.py
│   │   │   └── documents_hybrid_search.py
│   │   ├── routes/                # REST API route handlers (18 files)
│   │   ├── services/              # Business logic layer
│   │   │   ├── connector_service.py
│   │   │   ├── llm_router_service.py
│   │   │   ├── new_streaming_service.py
│   │   │   └── reranker_service.py
│   │   ├── tasks/
│   │   │   └── celery_tasks/      # Async background tasks
│   │   ├── config/                # Config & environment setup
│   │   ├── db.py                  # SQLAlchemy ORM models & enums
│   │   └── celery_app.py
│   ├── alembic/                   # Database migrations
│   ├── main.py
│   ├── pyproject.toml
│   └── .env.example
│
├── nbd_web/                        # Next.js frontend (TypeScript)
│   ├── app/
│   │   ├── (home)/                # Landing page
│   │   ├── auth/                  # Đăng nhập / Đăng ký
│   │   ├── dashboard/
│   │   │   └── [search_space_id]/
│   │   │       └── new-chat/      # Giao diện chat chính
│   │   ├── admin/                 # Admin panel
│   │   └── public/                # Trang chia sẻ công khai
│   ├── lib/
│   │   ├── apis/                  # API service layer (15+ services)
│   │   ├── hooks/                 # Custom React hooks
│   │   └── utils/
│   ├── components/
│   │   ├── chat/                  # Chat UI components
│   │   ├── documents/             # Document management
│   │   └── ui/                   # Radix UI base components
│   ├── package.json
│   └── .env.example
│
├── nbd_browser_extension/          # Plasmo browser extension
│   ├── popup.tsx                  # Extension popup
│   ├── contents/                  # Content scripts
│   ├── background/                # Service worker
│   └── package.json
│
├── docker/                         # Docker Compose configurations
│   ├── docker-compose.yml         # Production
│   ├── docker-compose.dev.yml     # Development
│   └── .env.example
│
├── Architecture/                   # HTML architecture diagrams
├── .github/                        # CI/CD workflows (GitHub Actions)
├── system_architecture.md
├── database_design.md
├── pipeline.md
└── README.md
```

---

## Công nghệ sử dụng

### Backend

| Thư viện | Phiên bản | Mục đích |
|---|---|---|
| FastAPI | 0.115.8 | Web framework chính |
| Python | 3.12 | Ngôn ngữ backend |
| SQLAlchemy | 2.0.47 | ORM (async) |
| asyncpg | 0.30.0 | Async PostgreSQL driver |
| pgvector | 0.3.6 | Vector similarity extension |
| Alembic | latest | Database migrations |
| Celery | 5.5.3 | Async task queue |
| Redis | 5.2.1 | Broker & cache |
| LiteLLM | 1.80.10 | Multi-provider LLM router |
| LangGraph | 1.0.5 | Agent framework |
| LangChain | 1.2.6 | LLM tooling |
| DeepAgents | 0.4.3 | Deep Agent framework |
| Docling | 2.15.0 | Document parser (PDF, DOCX, v.v.) |
| Chonkie | 1.5.0 | Text chunking |
| Unstructured | latest | Alternative document parser |
| Flashrank Rerankers | 0.7.1 | Result reranking |
| FastAPI Users | 15.0.3 | Auth (JWT + OAuth) |
| SlowAPI | 0.1.9 | Rate limiting (Redis-backed) |

### Frontend

| Thư viện | Phiên bản | Mục đích |
|---|---|---|
| Next.js | 16.1.0 | React framework (App Router) |
| React | 19.2.3 | UI library |
| Tailwind CSS | 4.1.11 | Styling |
| Plate.js | 52.0.17 | Rich text editor |
| Jotai | 2.15.1 | Atomic state management |
| TanStack Query | 5.90.7 | Data fetching & caching |
| TanStack Table | 8.21.3 | Data table |
| Radix UI | latest | Accessible UI components |
| React Hook Form | 7.61.1 | Form management |
| Zod | 4.2.1 | Schema validation |
| Assistant UI | latest | Chat interface components |
| next-intl | 4.6.1 | Internationalization |
| PostHog | 1.336.1 | Product analytics |
| Biome | 2.4.6 | Linting & formatting |

### Browser Extension

| Thư viện | Phiên bản | Mục đích |
|---|---|---|
| Plasmo | 0.90.5 | Extension framework (MV3) |
| React | 18.2.0 | UI |
| dom-to-semantic-markdown | 1.2.11 | HTML → Markdown conversion |
| Tailwind CSS | 3.4.10 | Styling |

### Hạ tầng

| Công nghệ | Mục đích |
|---|---|
| PostgreSQL 16 + pgvector | Primary database & vector store |
| Redis 8 | Celery broker, cache, rate limiting |
| Docker / Docker Compose | Container orchestration |
| GitHub Actions | CI/CD pipelines |
| GitHub Container Registry | Docker image hosting |

---

## Yêu cầu hệ thống

| Công cụ | Phiên bản khuyến nghị | Ghi chú |
|---|---|---|
| **Docker Desktop** | Latest | Bắt buộc cho PostgreSQL & Redis |
| **Python** | 3.12 | Chính xác 3.12 |
| **uv** | Latest | Trình quản lý gói Python tốc độ cao |
| **Node.js** | 22.0.0+ | Yêu cầu bởi nbd_web |
| **pnpm** | 11.5.2+ | Package manager cho frontend & extension |

Cài đặt `uv`:
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## Hướng dẫn cài đặt & khởi chạy

### 1. Khởi chạy cơ sở hạ tầng (Docker)

```bash
cd docker

# Sao chép file cấu hình môi trường
cp .env.example .env
# Chỉnh sửa .env nếu cần thay đổi port hoặc credentials mặc định

# Khởi chạy PostgreSQL + pgvector, Redis
docker-compose -f docker-compose.dev.yml up -d

# Kiểm tra các container đang chạy
docker ps
```

> Mặc định: PostgreSQL tại `localhost:5432`, Redis tại `localhost:6379`

---

### 2. Backend (FastAPI)

```bash
cd nbd_backend

# Sao chép và cấu hình biến môi trường
cp .env.example .env
# Điền DATABASE_URL, REDIS URL, LLM API keys vào .env (xem phần Biến môi trường)

# Cài đặt dependencies
uv sync

# Chạy database migration
uv run alembic upgrade head

# Khởi chạy API server
uv run uvicorn main:app --reload --port 8000
```

Mở terminal mới để chạy Celery Worker:
```bash
cd nbd_backend

# Worker mặc định (xử lý document indexing, notification, v.v.)
uv run celery -A app.celery_app.celery worker --loglevel=info

# (Optional) Worker riêng cho connector tasks
uv run celery -A app.celery_app.celery worker -Q connectors --loglevel=info

# (Optional) Celery Beat cho scheduled tasks
uv run celery -A app.celery_app.celery beat --loglevel=info
```

API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 3. Frontend (Next.js)

```bash
cd nbd_web

# Sao chép và cấu hình biến môi trường
cp .env.example .env
# Đặt NEXT_PUBLIC_FASTAPI_BACKEND_URL=http://localhost:8000

# Cài đặt dependencies
pnpm install

# Khởi chạy ở chế độ development
pnpm dev
```

Ứng dụng chạy tại: [http://localhost:3000](http://localhost:3000)

---

### 4. Browser Extension (Plasmo)

```bash
cd nbd_browser_extension

# Cài đặt dependencies
pnpm install

# Build development
pnpm dev
```

Load extension vào trình duyệt:
1. Mở Chrome → `chrome://extensions/`
2. Bật **Developer mode** (góc trên phải)
3. Chọn **Load unpacked**
4. Trỏ đến thư mục `build/chrome-mv3-dev`

Build production:
```bash
pnpm build
# Output: build/chrome-mv3-prod/
```

---

### 5. Triển khai Production

```bash
cd docker

cp .env.example .env
# Cấu hình tất cả biến môi trường production trong .env

# Kéo và chạy toàn bộ stack (prebuilt images từ ghcr.io)
docker-compose up -d
```

Stack production bao gồm: PostgreSQL, Redis, Backend (FastAPI + Uvicorn), Celery Worker, Frontend (Next.js).

---

## Biến môi trường

### Backend (`nbd_backend/.env`)

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/nfd_db

# Redis / Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
REDIS_APP_URL=redis://localhost:6379/1

# Authentication
SECRET_KEY=your-secret-key-here           # JWT secret (bắt buộc)
AUTH_TYPE=LOCAL                            # LOCAL hoặc GOOGLE

# OAuth (nếu AUTH_TYPE=GOOGLE)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# LLM & Embedding
EMBEDDING_MODEL=text-embedding-3-small    # Model embedding mặc định
OPENAI_API_KEY=sk-...                      # OpenAI API key
ANTHROPIC_API_KEY=sk-ant-...              # Anthropic (Claude)
GEMINI_API_KEY=...                         # Google Gemini

# ETL / Document Processing
ETL_SERVICE=DOCLING                        # DOCLING | UNSTRUCTURED | LLAMACLOUD
LLAMACLOUD_API_KEY=...                     # Nếu dùng LlamaCloud

# Connectors (tuỳ chọn)
SLACK_CLIENT_ID=...
SLACK_CLIENT_SECRET=...
GOOGLE_DRIVE_CLIENT_ID=...
GOOGLE_DRIVE_CLIENT_SECRET=...
JIRA_CLIENT_ID=...
JIRA_CLIENT_SECRET=...

# Monitoring (tuỳ chọn)
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=...
```

### Frontend (`nbd_web/.env`)

```env
NEXT_PUBLIC_FASTAPI_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_FASTAPI_BACKEND_AUTH_TYPE=LOCAL     # LOCAL hoặc GOOGLE
NEXT_PUBLIC_ETL_SERVICE=DOCLING
NEXT_PUBLIC_DEPLOYMENT_MODE=self-hosted          # self-hosted hoặc cloud
```

### Docker (`docker/.env`)

```env
# Database
DB_USER=nfd
DB_PASSWORD=nfd_password
DB_NAME=nfd_db
POSTGRES_PORT=5432

# Redis
REDIS_PORT=6379

# Services
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

---

## API Endpoints

Base URL: `http://localhost:8000`

### Authentication

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/auth/register` | Đăng ký tài khoản mới |
| POST | `/auth/jwt/login` | Đăng nhập, nhận JWT token |
| POST | `/auth/jwt/logout` | Đăng xuất |
| POST | `/auth/refresh` | Làm mới access token |
| POST | `/auth/forgot-password` | Gửi email đặt lại mật khẩu |
| POST | `/auth/verify-token` | Xác minh email |

### Search Spaces (Workspaces)

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/api/v1/searchspaces` | Tạo search space mới |
| GET | `/api/v1/searchspaces` | Danh sách search spaces của user |
| GET | `/api/v1/searchspaces/{id}` | Chi tiết search space |
| PUT | `/api/v1/searchspaces/{id}` | Cập nhật search space |
| DELETE | `/api/v1/searchspaces/{id}` | Xóa search space |
| GET | `/api/v1/searchspaces/{id}/stats` | Thống kê (số tài liệu, chunk, v.v.) |

### Documents

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/api/v1/documents` | Tạo document từ text/URL |
| POST | `/api/v1/documents/fileupload` | Upload file (PDF, DOCX, v.v.) |
| GET | `/api/v1/documents` | Danh sách documents (phân trang) |
| GET | `/api/v1/documents/{id}` | Chi tiết document |
| PUT | `/api/v1/documents/{id}` | Cập nhật document |
| DELETE | `/api/v1/documents/{id}` | Xóa document |
| GET | `/api/v1/documents/{id}/chunks` | Danh sách chunks với embeddings |
| GET | `/api/v1/documents/search` | Tìm kiếm document theo tiêu đề |

### Chat & Conversations

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/api/v1/threads` | Tạo chat thread mới |
| GET | `/api/v1/threads` | Danh sách threads (sidebar) |
| GET | `/api/v1/threads/{id}` | Load thread và toàn bộ messages |
| PUT | `/api/v1/threads/{id}` | Đổi tên / cập nhật visibility |
| DELETE | `/api/v1/threads/{id}` | Xóa thread |
| POST | `/api/v1/new_chat` | **Gửi query — trả về SSE stream** |
| POST | `/api/v1/threads/{id}/messages` | Thêm message vào thread |
| POST | `/api/v1/threads/{id}/regenerate` | Tạo lại câu trả lời cuối |
| POST | `/api/v1/threads/{id}/resume` | Tiếp tục chat bị gián đoạn |

### Connectors (Data Sources)

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/api/v1/connectors` | Tạo connector mới |
| GET | `/api/v1/connectors` | Danh sách connectors |
| PUT | `/api/v1/connectors/{id}` | Cập nhật cấu hình |
| DELETE | `/api/v1/connectors/{id}` | Xóa connector |
| POST | `/api/v1/connectors/{id}/index` | Trigger đồng bộ thủ công |
| GET | `/api/v1/connectors/{id}/status` | Trạng thái đồng bộ |

### RBAC — Members & Roles

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/api/v1/roles` | Tạo vai trò tùy chỉnh |
| GET | `/api/v1/roles` | Danh sách vai trò |
| PUT | `/api/v1/roles/{id}` | Cập nhật vai trò |
| DELETE | `/api/v1/roles/{id}` | Xóa vai trò |
| POST | `/api/v1/members/invite` | Mời thành viên vào workspace |
| GET | `/api/v1/members` | Danh sách thành viên |
| PUT | `/api/v1/members/{user_id}/role` | Thay đổi vai trò thành viên |
| DELETE | `/api/v1/members/{user_id}` | Xóa thành viên khỏi workspace |

### LLM & Models

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/api/v1/models` | Danh sách LLM models hỗ trợ |
| GET | `/api/v1/llm-configs` | Danh sách cấu hình LLM |
| POST | `/api/v1/llm-configs` | Thêm cấu hình LLM tùy chỉnh |
| PUT | `/api/v1/llm-configs/{id}` | Cập nhật cấu hình LLM |

### Utilities

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/v1/notifications` | Danh sách notifications |
| POST | `/api/v1/notes` | Tạo ghi chú |
| GET | `/api/v1/logs` | Xem logs (có filter) |

---

## Luồng xử lý dữ liệu

### Upload & Indexing Document

```
User upload file
      ↓
FastAPI nhận file → tạo Document record (status: PENDING)
      ↓
Enqueue Celery task
      ↓
Celery Worker:
  1. Parse document (Docling / Unstructured / LlamaCloud)
  2. Chunk text (Chonkie — semantic / sentence / token chunking)
  3. Embed chunks (LiteLLM → embedding model)
  4. Lưu chunks + vectors vào PostgreSQL + pgvector
  5. Cập nhật Document status → COMPLETED
      ↓
ElectricSQL → Frontend cập nhật UI thời gian thực
```

### Chat Query (RAG Flow)

```
User gửi câu hỏi
      ↓
POST /api/v1/new_chat → SSE stream bắt đầu
      ↓
Deep Agent (LangGraph):
  1. Phân tích intent
  2. Gọi tool: knowledge_base search
      ↓
  Hybrid Search:
    a. Dense search (pgvector cosine similarity)
    b. Sparse search (PostgreSQL full-text search)
    c. RRF fusion (kết hợp 2 kết quả)
    d. Reranking (Flashrank)
      ↓
  3. Tổng hợp context từ chunks đã retrieve
  4. Gọi LLM (LiteLLM → provider đã cấu hình)
  5. Stream response về Frontend qua SSE
      ↓
Frontend render câu trả lời + source citations theo thời gian thực
```

---

## Hybrid RAG Pipeline

Hệ thống sử dụng **Hybrid Search** kết hợp hai phương pháp tìm kiếm:

```
Query
  ├── Dense Search ──────────────────────────────────────┐
  │   (pgvector cosine similarity với embedding vector)   │
  │                                                        ├── RRF Fusion ── Reranker ── Top-K chunks
  └── Sparse Search ─────────────────────────────────────┘
      (PostgreSQL full-text search với tsvector/tsquery)
```

**Reciprocal Rank Fusion (RRF):**
```
RRF_score(d) = Σ 1 / (k + rank_i(d))
```
- `k` = hằng số (thường = 60)
- `rank_i(d)` = thứ hạng của document `d` trong kết quả từ nguồn `i`

**Reranking:** Sử dụng Flashrank để sắp xếp lại kết quả cuối cùng trước khi đưa vào LLM context.

---

## CI/CD & Versioning

### Tự động tạo version tag

Khi push code lên nhánh `main` hoặc `dev` có thay đổi trong `nbd_backend/**` hoặc `nbd_web/**`:

1. Đọc phiên bản cơ sở từ `nbd_backend/pyproject.toml` (ví dụ: `0.0.13`)
2. Tìm build number lớn nhất hiện có trên remote (ví dụ: `0.0.13.5`)
3. Tăng build number → `0.0.13.6`, tạo git tag mới
4. Push tag lên GitHub
5. GitHub Actions build Docker images và push lên GHCR với tag tương ứng

### Docker images

```bash
# Pull image production mới nhất
docker pull ghcr.io/<org>/nfd-backend:0.0.13.6
docker pull ghcr.io/<org>/nfd-web:0.0.13.6
```

---

## Tài liệu tham khảo

| Tài liệu | Mô tả |
|---|---|
| [system_architecture.md](system_architecture.md) | Phân tích kiến trúc chi tiết (Chapter 2) |
| [database_design.md](database_design.md) | Thiết kế cơ sở dữ liệu, ERD, các bảng chính |
| [pipeline.md](pipeline.md) | Phân tích chi tiết Hybrid RAG pipeline |
| [activity_diagram.md](activity_diagram.md) | Activity diagrams cho các luồng chính |
| [SOURCE_FLOW_SUMMARY.md](SOURCE_FLOW_SUMMARY.md) | Tóm tắt runtime flow theo từng thành phần |
| [Architecture/](Architecture/) | Sơ đồ kiến trúc dạng HTML (từ Mermaid) |
| [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger UI — API docs tự động (khi dev) |
| [http://localhost:8000/redoc](http://localhost:8000/redoc) | ReDoc — API docs thay thế (khi dev) |
