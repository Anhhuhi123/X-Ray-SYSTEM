# Sequence Diagram (Biểu đồ Tuần tự)

## 1. Upload và Phân tích Tài liệu (Thay thế cho Upload và Phân tích ảnh)

> **Ghi chú**: Chức năng phân tích ảnh và Vision Service không tìm thấy trong source. Dưới đây là sơ đồ mô tả quá trình tải lên tài liệu (File, Web) và xử lý bất đồng bộ thông qua Celery Worker để trích xuất văn bản thay cho luồng xử lý ảnh.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend as Next.js Frontend
    participant Backend as FastAPI Backend
    participant Worker as Celery Worker
    participant DB as PostgreSQL (pgvector)

    User->>Frontend: Chọn File và nhấn Tải lên
    Frontend->>Backend: POST /api/v1/documents/fileupload
    activate Backend
    
    Backend->>DB: Tạo bản ghi Document (Status: Pending)
    activate DB
    DB-->>Backend: Trả về Document ID
    deactivate DB
    
    Backend->>Worker: Enqueue Task (document_id) qua Redis
    Backend-->>Frontend: Trả về HTTP 200 (Bắt đầu xử lý)
    deactivate Backend
    
    Frontend-->>User: Hiển thị trạng thái "Đang xử lý"

    activate Worker
    Worker->>DB: Cập nhật Status = Processing
    Worker->>Worker: Đọc nội dung File (Docling/Unstructured)
    Worker->>Worker: Phân mảnh văn bản (Chonkie)
    Worker->>Backend: Gọi API / Internal LLM sinh Embeddings
    Worker->>DB: Lưu Chunks và Vectors
    Worker->>DB: Cập nhật Status = Ready
    deactivate Worker
    
    DB-->>Frontend: Bắn tín hiệu Realtime Sync (ElectricSQL)
    Frontend-->>User: Hiển thị trạng thái "Hoàn thành"
```

---

## 2. Hybrid RAG Query

Sơ đồ thể hiện quá trình người dùng đặt câu hỏi, tác nhân Deep Agent quyết định tìm kiếm (Retriever), thực hiện Hybrid Search (Dense + Sparse) và hợp nhất bằng RRF, cuối cùng trả kết quả về qua luồng SSE.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend as Next.js Frontend
    participant Backend as FastAPI Backend (Deep Agent)
    participant Retriever as Connector Service (Retriever)
    participant VectorDB as PostgreSQL (pgvector)
    participant LLM as LiteLLM API

    User->>Frontend: Gửi tin nhắn mới trong Chat
    Frontend->>Backend: POST /api/v1/new_chat (Tạo SSE Stream)
    
    activate Backend
    Backend->>Backend: Load Lịch sử hội thoại & Checkpointer
    Backend->>Backend: Khởi tạo Deep Agent (LangGraph)
    Backend->>LLM: Gửi Prompt và yêu cầu Reasoning
    activate LLM
    LLM-->>Backend: Trả về Action: Gọi tool "Search Knowledge Base"
    deactivate LLM
    
    Backend->>Retriever: Thực hiện Hybrid Search (Query, Search Space ID)
    activate Retriever
    
    par Dense Search
        Retriever->>LLM: Sinh Embedding cho Query
        LLM-->>Retriever: Trả về Query Vector
        Retriever->>VectorDB: L2/Cosine Similarity Search
        VectorDB-->>Retriever: Trả về Dense Chunks
    and Sparse Search
        Retriever->>VectorDB: Full Text Search (TsVector)
        VectorDB-->>Retriever: Trả về Sparse Chunks
    end
    
    Retriever->>Retriever: Trộn kết quả bằng Reciprocal Rank Fusion (RRF)
    Retriever-->>Backend: Trả về Top Chunks & Metadata
    deactivate Retriever
    
    Backend->>LLM: Gửi Prompt tổng hợp (Chat History + Chunks Context)
    activate LLM
    
    loop Server-Sent Events (SSE)
        LLM-->>Backend: Stream Token (Chunk)
        Backend-->>Frontend: Trả về Text Delta Event
        Frontend-->>User: Cập nhật UI (Typing effect)
    end
    deactivate LLM
    
    Backend->>VectorDB: Lưu Message & Citation IDs vào DB
    Backend-->>Frontend: Trả về Event "Done"
    deactivate Backend
```

---

## 3. Xem lịch sử hội thoại (Thay thế cho Xem lịch sử phân tích ảnh)

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend as Next.js Frontend
    participant Backend as FastAPI Backend
    participant DB as PostgreSQL

    User->>Frontend: Mở trang Dashboard / Lịch sử Chat
    Frontend->>Backend: GET /api/v1/threads (Kèm Access Token)
    activate Backend
    
    Backend->>Backend: Xác thực Auth Token (FastAPI Users)
    Backend->>DB: Truy vấn danh sách Threads (Có phân quyền RBAC)
    activate DB
    DB-->>Backend: Trả về danh sách NewChatThread
    deactivate DB
    
    Backend-->>Frontend: Trả về HTTP 200 (JSON Threads)
    deactivate Backend
    
    Frontend-->>User: Hiển thị danh sách Lịch sử Hội thoại
    
    User->>Frontend: Click vào 1 Hội thoại cụ thể
    Frontend->>Backend: GET /api/v1/threads/{id}/messages
    activate Backend
    
    Backend->>DB: Fetch NewChatMessage theo thread_id
    activate DB
    DB-->>Backend: Trả về toàn bộ tin nhắn
    deactivate DB
    
    Backend-->>Frontend: HTTP 200 (JSON Messages)
    deactivate Backend
    
    Frontend-->>User: Render nội dung hội thoại
```
