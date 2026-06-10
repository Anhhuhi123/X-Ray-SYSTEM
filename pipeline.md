# Phân tích Pipeline Hệ thống NFD — Hybrid RAG & Ứng dụng Web

> Dựa trên source code: `nbd_backend/` và `nbd_web/`

---

## 3.6. Xây dựng hệ thống Hybrid RAG

NFD sử dụng kiến trúc **Hybrid RAG** kết hợp hai phương pháp truy xuất: **Dense Retrieval** (tìm kiếm ngữ nghĩa theo vector embedding) và **Sparse Retrieval** (tìm kiếm từ khóa full-text), sau đó hợp nhất kết quả bằng thuật toán **Reciprocal Rank Fusion (RRF)** trước khi đưa vào LLM sinh câu trả lời.

---

### 3.6.1. Xây dựng kho tri thức (Indexing Pipeline)

Kho tri thức được xây dựng qua một pipeline lập chỉ mục gồm 5 bước nối tiếp nhau, xử lý bất đồng bộ qua Celery task queue:

```
Tài liệu đầu vào
(File PDF/Word, URL, Ghi chú, Google Drive, Obsidian...)
        │
        ▼
┌──────────────────────────────────────┐
│  Bước 1: Document Preparation        │
│  - Tính content_hash & unique_hash   │
│  - Kiểm tra trùng lặp (dedup)        │
│  - Đặt trạng thái: pending → process │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│  Bước 2: Document Chunking           │
│  parse_markdown_into_sections()      │
│  - Dùng regex tìm ATX headings       │
│  - Stack-based algorithm phân cấp   │
│    heading h1→h6 thành sections      │
│  - Mỗi section → N ParsedChunk       │
│  - Gắn section_type heuristically    │
│    (title/chapter/introduction/...)  │
│  - Chunk body text bằng chonkie lib  │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│  Bước 3: Embedding                   │
│  - Gọi embedding model qua LiteLLM  │
│  - Hỗ trợ SentenceTransformers      │
│    (local) hoặc API-based            │
│  - Truncate theo context window      │
│  - Tạo vector float[] cho mỗi chunk  │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│  Bước 4: Summarization (tùy chọn)   │
│  - LLM tóm tắt document lớn         │
│  - Binary search để fit context win  │
│  - Bao gồm document metadata         │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│  Bước 5: Persistence                 │
│  - Lưu DocumentSection vào DB        │
│  - Resolve temp UUID → DB UUID       │
│  - Lưu Chunk với embedding vector    │
│  - Cập nhật trạng thái: → ready      │
└──────────────────────────────────────┘
```

**Cấu trúc dữ liệu sau lập chỉ mục:**

| Bảng | Mô tả |
|------|-------|
| `Document` | Tài liệu gốc — metadata, document_type, content_hash, trạng thái |
| `DocumentSection` | Section phân cấp theo heading — giữ quan hệ parent-child |
| `Chunk` | Đoạn văn bản nhỏ — nội dung + `embedding vector(float[])` |

**Loại tài liệu được hỗ trợ:**

| DocumentType | Nguồn |
|---|---|
| `FILE` | Upload trực tiếp (PDF, Word, .txt...) |
| `EXTENSION` | Trình duyệt extension lưu trang web |
| `NOTE` | Ghi chú tạo trong NFD |
| `YOUTUBE_VIDEO` | Transcript video YouTube |
| `OBSIDIAN_CONNECTOR` | Vault Obsidian markdown |
| `COMPOSIO_GOOGLE_DRIVE_CONNECTOR` | Google Drive qua Composio |

---

### 3.6.2. Dense Retrieval

Dense Retrieval là phương pháp tìm kiếm ngữ nghĩa dựa trên vector embedding — mã hóa câu truy vấn thành một vector trong không gian ngữ nghĩa cao chiều, sau đó tính độ tương đồng cosine với các vector đã lập chỉ mục trong cơ sở dữ liệu.

**Thực thi qua pgvector — toán tử `<=>`  (cosine distance):**

```python
# Nguồn: nbd_backend/app/retriever/chunks_hybrid_search.py

# 1. Nhúng câu truy vấn thành vector
embedding_model = config.embedding_model_instance
query_embedding = embedding_model.embed(query_text)   # float[]

# 2. Xây dựng CTE với rank theo cosine distance
semantic_search_cte = (
    select(
        Chunk.id,
        func.rank()
            .over(order_by=Chunk.embedding.op("<=>")(query_embedding))
            .label("rank"),
    )
    .join(Document, Chunk.document_id == Document.id)
    .where(*base_conditions)
    .order_by(Chunk.embedding.op("<=>")(query_embedding))
    .limit(n_results)          # n_results = top_k * 5
    .cte("semantic_search")
)
```

**Đặc điểm:**
- Tìm tài liệu **ngữ nghĩa tương đồng** dù không dùng đúng từ khóa
- Chạy trực tiếp trên PostgreSQL + extension **pgvector**
- Lấy `top_k × 5` kết quả (overfetch) để RRF có đủ tập ứng viên
- Thực thi song song với Sparse Retrieval qua SQLAlchemy CTE

---

### 3.6.3. Sparse Retrieval

Sparse Retrieval là tìm kiếm từ khóa dựa trên PostgreSQL Full-Text Search (FTS) — chuyển đổi văn bản thành `tsvector` và truy vấn thành `tsquery`, sau đó xếp hạng theo `ts_rank_cd` (Coverage Density ranking).

**Thực thi qua PostgreSQL FTS:**

```python
# Nguồn: nbd_backend/app/retriever/chunks_hybrid_search.py

# 1. Tạo tsvector và tsquery
tsvector = func.to_tsvector("english", Chunk.content)
tsquery  = func.plainto_tsquery("english", query_text)

# 2. Xây dựng CTE với rank theo ts_rank_cd
keyword_search_cte = (
    select(
        Chunk.id,
        func.rank()
            .over(order_by=func.ts_rank_cd(tsvector, tsquery).desc())
            .label("rank"),
    )
    .join(Document, Chunk.document_id == Document.id)
    .where(*base_conditions)
    .where(tsvector.op("@@")(tsquery))   # chỉ lấy kết quả khớp
    .order_by(func.ts_rank_cd(tsvector, tsquery).desc())
    .limit(n_results)
    .cte("keyword_search")
)
```

**Đặc điểm:**
- Tìm kiếm **từ khóa chính xác** và biến thể từ ngữ (stemming tiếng Anh)
- `@@` operator lọc chỉ giữ chunk thực sự chứa từ khóa
- `ts_rank_cd` xếp hạng theo mật độ phân phối từ khóa trong đoạn văn
- Xử lý trong cùng câu query SQL với Dense Retrieval — không cần round-trip mạng bổ sung
- **Bổ trợ cho Dense Retrieval** khi câu hỏi chứa tên riêng, mã code, thuật ngữ kỹ thuật chính xác

---

### 3.6.4. Reciprocal Rank Fusion (RRF)

RRF là thuật toán hợp nhất kết quả từ nhiều phương pháp truy xuất mà không cần chuẩn hóa điểm số. Điểm RRF của mỗi tài liệu được tính bằng tổng nghịch đảo thứ hạng từ mỗi danh sách:

**Công thức:**

```
RRF_score(doc) = Σ  1 / (k + rank_i(doc))
               i∈{dense, sparse}
```

Trong đó `k = 60` (hằng số điều chỉnh độ ảnh hưởng của thứ hạng cao).

**Triển khai SQL — FULL OUTER JOIN hai CTE:**

```python
# Nguồn: nbd_backend/app/retriever/chunks_hybrid_search.py

k = 60

final_query = (
    select(
        Chunk,
        (
            func.coalesce(1.0 / (k + semantic_search_cte.c.rank), 0.0)
            + func.coalesce(1.0 / (k + keyword_search_cte.c.rank), 0.0)
        ).label("score"),
    )
    .select_from(
        semantic_search_cte.outerjoin(
            keyword_search_cte,
            semantic_search_cte.c.id == keyword_search_cte.c.id,
            full=True,   # FULL OUTER JOIN — giữ kết quả chỉ có ở 1 phía
        )
    )
    .join(
        Chunk,
        Chunk.id == func.coalesce(semantic_search_cte.c.id, keyword_search_cte.c.id),
    )
    .order_by(text("score DESC"))
    .limit(top_k)
)
```

**Toàn bộ luồng Hybrid Search từ query đến kết quả:**

```
Câu truy vấn người dùng
        │
        ▼
  [Tính embedding 1 lần] ──── dùng lại cho cả Dense & Sparse
        │
        ├──────────────────────────────────────┐
        ▼                                      ▼
  CTE: semantic_search                  CTE: keyword_search
  (Dense — cosine distance)             (Sparse — ts_rank_cd)
  top_k × 5 chunks                      top_k × 5 chunks
  rank 1, 2, 3, ...                      rank 1, 2, 3, ...
        │                                      │
        └──────────────┬───────────────────────┘
                       ▼
            FULL OUTER JOIN trên chunk.id
                       │
                       ▼
         Tính điểm RRF cho từng chunk:
         score = coalesce(1/(60+rank_dense), 0)
               + coalesce(1/(60+rank_sparse), 0)
                       │
                       ▼
         Sắp xếp theo score DESC, lấy top_k chunks
                       │
                       ▼
         Gom nhóm theo Document (doc_id)
         → giữ tối đa 30 chunks/document
                       │
                       ▼
         Trả về list[dict]:
         {
           document_id, title, document_type,
           score (float),
           chunks: [{chunk_id, content}, ...],
           content: "<toàn bộ nội dung nối lại>"
         }
```

**Ưu điểm của RRF trong hệ thống này:**
- **Không cần chuẩn hóa điểm số** — Dense score (0~1) và Sparse score (ts_rank) có đơn vị khác nhau, RRF giải quyết vấn đề này
- **FULL OUTER JOIN** đảm bảo tài liệu chỉ xuất hiện ở một phương pháp không bị loại bỏ
- `coalesce(..., 0.0)` xử lý trường hợp chunk không có trong một trong hai danh sách
- **chunk_id được giữ nguyên** xuyên suốt pipeline — cho phép trích dẫn `[citation:<chunk_id>]`

**Budget phân bổ ngữ cảnh theo thứ hạng:**

```python
# Tài liệu xếp cao hơn nhận nhiều chunks hơn
doc_fraction = 0.40 / (1 + doc_idx * 0.35)
# rank 0 → 40% budget → ~6 chunks
# rank 1 → 30% budget → ~4 chunks
# rank 2 → 24% budget → ~3 chunks (floor)
```

---

### 3.6.5. Sinh câu trả lời

Sau khi truy xuất tài liệu liên quan, hệ thống sử dụng **LangGraph Deep Agent** để sinh câu trả lời có trích dẫn nguồn.

**Kiến trúc Agent (LangGraph Stateful Graph):**

```
Người dùng nhập câu hỏi
        │
        ▼
┌────────────────────────────────────────────┐
│         NFD Deep Agent (LangGraph)          │
│                                            │
│  System Prompt:                            │
│  - Hướng dẫn sử dụng tool                 │
│  - Bật/tắt citation [citation:<chunk_id>]  │
│  - Custom instructions từ NewLLMConfig     │
│                                            │
│  Tools Registry:                           │
│  ┌─────────────────────────────────────┐   │
│  │ search_knowledge_base               │   │
│  │  - query, top_k, connectors, dates  │   │
│  │  - Gọi Hybrid RRF search            │   │
│  │  - Trả về XML context có chunk_id   │   │
│  ├─────────────────────────────────────┤   │
│  │ search_nfd_docs                     │   │
│  │  - Tìm trong tài liệu hệ thống NFD  │   │
│  │  - Parallel docs + chunks search    │   │
│  ├─────────────────────────────────────┤   │
│  │ generate_report                     │   │
│  │  - Sinh báo cáo có cấu trúc         │   │
│  ├─────────────────────────────────────┤   │
│  │ write_todos (TodoListMiddleware)     │   │
│  │  - Lập kế hoạch cho task phức tạp   │   │
│  └─────────────────────────────────────┘   │
│                                            │
│  State Persistence: PostgreSQL Checkpointer│
│  (giữ lịch sử hội thoại xuyên session)    │
└──────────────────┬─────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
  Gọi tool                 Sinh trực tiếp
  (search/report)          (nếu đủ thông tin)
        │
        ▼
  Kết quả XML:
  <document>
    <chunk id='123'><![CDATA[nội dung]]></chunk>
  </document>
        │
        ▼
  LLM tổng hợp câu trả lời
  với trích dẫn [citation:123]
        │
        ▼
  Streaming Response (SSE)
  → Frontend nhận từng token theo thời gian thực
```

**Luồng tìm kiếm đa connector song song:**

```python
# nbd_backend/app/agents/new_chat/tools/knowledge_base.py

# Tính embedding 1 lần — dùng lại cho TẤT CẢ connector
precomputed_embedding = embedding_model.embed(query)

# Tìm kiếm song song tối đa 4 connector cùng lúc
semaphore = asyncio.Semaphore(4)
connector_results = await asyncio.gather(
    *[_search_one_connector(c) for c in connectors]
)
# Mỗi connector gọi _combined_rrf_search với shared embedding
# → tránh tính embedding nhiều lần
```

**Context XML format đưa vào LLM:**

```xml
<document>
  <document_metadata>
    <document_id>42</document_id>
    <document_type>FILE</document_type>
    <title><![CDATA[Báo cáo Q3 2024]]></title>
    <url><![CDATA[https://...]]></url>
    <metadata_json><![CDATA[{...}]]></metadata_json>
  </document_metadata>
  <document_content>
    <chunk id='123'><![CDATA[Doanh thu Q3 đạt 15 tỷ...]]></chunk>
    <chunk id='124'><![CDATA[Chi phí vận hành giảm 8%...]]></chunk>
  </document_content>
</document>
```

**Quản lý context window động:**

| Thông số | Giá trị |
|---|---|
| Budget tối thiểu | 20,000 ký tự |
| Budget tối đa | 200,000 ký tự |
| Tỷ lệ context dành cho tool output | 25% context window |
| Ký tự/token ước lượng | 4 |
| Chunk tối đa/ký tự | 8,000 |
| Decay giữa các tài liệu theo rank | 0.35 |

---

## 3.7. Xây dựng ứng dụng Web

### 3.7.1. Backend

**Framework & Công nghệ:**

| Thành phần | Công nghệ | Phiên bản |
|---|---|---|
| Web framework | FastAPI | Mới nhất |
| Runtime | Python | 3.12 |
| Task queue | Celery + Redis | 5.5.3 |
| LLM abstraction | LiteLLM | ≥1.80.10 |
| Agent framework | LangGraph | ≥1.0.5 |
| ORM | SQLAlchemy (async) | ≥2.0 |
| DB driver | asyncpg | ≥0.30.0 |

**Cấu trúc API Routes chính:**

| Route file | Chức năng |
|---|---|
| `new_chat_routes.py` | Chat threads, messages, SSE streaming |
| `documents_routes.py` | Upload, tìm kiếm, xóa tài liệu |
| `nfd_docs_routes.py` | Tìm kiếm tài liệu hệ thống |
| `rbac_routes.py` | Phân quyền người dùng (Owner/Editor/Viewer) |
| `new_llm_config_routes.py` | Cấu hình LLM model theo search space |
| `composio_routes.py` | Tích hợp Google Drive qua Composio |
| `notifications_routes.py` | Thông báo realtime |

**Xử lý bất đồng bộ:**
- Celery Worker xử lý indexing document trong background
- Redis làm message broker và cache
- Rate limiting dùng Redis với fallback in-memory (slowapi)
- LangSmith tracing hỗ trợ debug AI pipeline

---

### 3.7.2. Frontend

**Framework & Core:**

| Thư viện | Phiên bản | Mục đích |
|---|---|---|
| Next.js | 16.1.0 | React framework (App Router) |
| React | 19.2.3 | UI framework |
| TypeScript | 5.8.3 | Type safety |
| Tailwind CSS | 4.1.11 | Utility-first styling |

**State Management & Data Fetching:**

| Thư viện | Phiên bản | Mục đích |
|---|---|---|
| Jotai | 2.15.1 | Atom-based global state |
| TanStack React Query | 5.90.7 | Server state, caching |
| jotai-tanstack-query | 0.11.0 | Kết hợp Jotai với React Query |
| React Hook Form | 7.61.1 | Form management |
| Zod | 4.2.1 | Schema validation |

**UI Components:**

| Thư viện | Phiên bản | Mục đích |
|---|---|---|
| Radix UI | Various | Accessible headless primitives |
| Plate.js | 52.0.x | Block-based rich text editor |
| @assistant-ui/react | 0.11.53 | Agentic chat UI |
| Lucide React | 0.577.0 | Icon library |
| Recharts | 3.8.1 | Charts & data visualization |
| Motion | 12.23.22 | Animation |
| Sonner | 2.0.6 | Toast notifications |

**Content Rendering:**

| Thư viện | Mục đích |
|---|---|
| react-markdown + remark-gfm | GitHub Flavored Markdown |
| remark-math + rehype-katex | Công thức toán học (LaTeX) |
| KaTeX | Render toán học phía client |
| Lowlight | Syntax highlighting code blocks |
| @streamdown/code, @streamdown/math | Streaming markdown/math rendering |

**Tiện ích:**

| Thư viện | Mục đích |
|---|---|
| next-intl | Đa ngôn ngữ (i18n) |
| next-themes | Dark/light mode |
| PostHog | Analytics |
| date-fns | Xử lý thời gian |
| react-dropzone | Upload file kéo thả |

**Cấu trúc thư mục:**

```
nbd_web/
├── app/                    # Next.js App Router pages
│   ├── (home)/             # Landing page
│   ├── dashboard/          # Knowledge base interface
│   ├── admin/              # Admin console
│   ├── chat/               # Chat interface
│   └── auth/               # Authentication pages
├── components/             # Reusable React components
├── atoms/                  # Jotai global state atoms
├── hooks/                  # Custom React hooks
├── lib/                    # Utilities, API clients
├── contexts/               # React Context providers
├── contracts/              # Zod type definitions
├── i18n/                   # Internationalization
└── content/                # Static MDX content
```

---

### 3.7.3. Database

**PostgreSQL + pgvector** là lựa chọn duy nhất, đóng vai trò vừa là relational database vừa là vector store — không cần hệ thống vector database riêng biệt.

**Schema chính:**

```
SearchSpace (kho tri thức của user)
    │
    ├── Document (tài liệu)
    │       │  document_type: FILE | EXTENSION | NOTE | YOUTUBE_VIDEO | ...
    │       │  status: JSONB {state: pending|processing|ready|failed|deleting}
    │       │  content_hash: deduplication
    │       │
    │       ├── DocumentSection (phân cấp markdown)
    │       │       heading_level, section_type, parent_id (self-ref)
    │       │
    │       └── Chunk (đoạn văn bản lập chỉ mục)
    │               content: text
    │               embedding: vector(float[])   ← pgvector
    │               chunk_order_in_section: int
    │
    ├── NewChatThread (luồng hội thoại)
    │       visibility: PRIVATE | PUBLIC
    │       │
    │       └── NewChatMessage (tin nhắn)
    │               role: user | assistant
    │               content: JSONB (streaming snapshot)
    │
    └── NewLLMConfig (cấu hình LLM per search space)
            provider, model_name, api_key, system_instructions
```

**Các extension PostgreSQL sử dụng:**
- **pgvector**: Lưu trữ và tìm kiếm vector embedding (toán tử `<=>` cosine distance)
- **tsvector/tsquery**: Full-text search built-in của PostgreSQL
- **JSONB**: Lưu metadata linh hoạt, trạng thái tài liệu

**ElectricSQL** được tích hợp để đồng bộ dữ liệu realtime từ PostgreSQL xuống client — đảm bảo UI cập nhật ngay khi tài liệu được index xong.

---

### 3.7.4. Tích hợp AI Pipeline

Điểm tích hợp giữa ứng dụng web và AI pipeline diễn ra theo luồng sau:

```
Frontend (Next.js)
        │
        │  POST /api/chat/threads/{id}/messages
        │  { query, search_space_id, ... }
        ▼
Backend (FastAPI)
        │
        ├── Khởi tạo LLM qua LiteLLM Router
        │   (dựa theo NewLLMConfig của search space)
        │
        ├── Khởi tạo PostgreSQL Checkpointer
        │   (lưu conversation state giữa các turn)
        │
        ├── Khám phá connectors & document types
        │   có sẵn trong search space
        │
        ├── create_nfd_deep_agent(
        │       llm, search_space_id, db_session,
        │       connector_service, checkpointer,
        │       agent_config, enabled_tools
        │   )
        │   → CompiledStateGraph (LangGraph)
        │
        ├── agent.astream_events(
        │       {"messages": [HumanMessage(query)]},
        │       config={"thread_id": thread_id}
        │   )
        │
        ▼
AI Pipeline thực thi (LangGraph loop):
        │
        ├── [Quyết định: dùng tool hay sinh trực tiếp?]
        │
        ├── Nếu cần tìm kiếm:
        │   └── search_knowledge_base(query, top_k, connectors)
        │           │
        │           ├── Tính embedding 1 lần
        │           ├── asyncio.gather() — tìm song song N connectors
        │           ├── Mỗi connector: _combined_rrf_search()
        │           │     ├── Dense CTE (pgvector)
        │           │     ├── Sparse CTE (PostgreSQL FTS)
        │           │     └── FULL OUTER JOIN + RRF score
        │           ├── Dedup theo document_id
        │           └── format_documents_for_context() → XML string
        │
        ├── LLM nhận context XML + system prompt
        │   → Sinh câu trả lời với [citation:chunk_id]
        │
        └── Streaming tokens qua Server-Sent Events (SSE)
                │
                ▼
        Frontend nhận stream
        → @assistant-ui/react render từng token
        → Citation [citation:123] hiển thị thành link
           trỏ đến chunk trong tài liệu gốc
```

**Cấu hình LLM động (NewLLMConfig):**
- Mỗi Search Space có thể cấu hình riêng: provider, model_name, api_key
- LiteLLM làm abstraction layer — hỗ trợ OpenAI, Anthropic, Gemini, Ollama...
- System instructions có thể tùy chỉnh per-user
- Bật/tắt citation feature theo cấu hình

**Deployment Infrastructure:**

```
Docker Compose
├── postgresql (pgvector extension)
├── redis (Celery broker + rate limit cache)
├── electricsql (realtime DB sync)
├── backend (FastAPI — uvicorn)
├── celery_worker (document indexing)
└── frontend (Next.js — Node 22)
```
