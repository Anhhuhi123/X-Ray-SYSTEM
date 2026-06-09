# Đặc tả Use Case (Use Case Specification)

## 1. Xác định Actor

Dựa trên mã nguồn, các tác nhân (Actors) tham gia vào hệ thống bao gồm:

- **User (Người dùng/Thành viên)**: Người dùng có tài khoản trên hệ thống NFD, thuộc một hoặc nhiều Search Space (không gian tìm kiếm) với vai trò như Viewer hoặc Editor.
- **Owner / Admin**: Người dùng sở hữu (Owner) hoặc có toàn quyền trên một Search Space, có quyền thiết lập cấu hình LLM, xoá Search Space và quản lý thành viên.
- **Deep Agent (AI System)**: Hệ thống tác nhân trí tuệ nhân tạo tương tác, đóng vai trò trả lời câu hỏi và tự động gọi các tool thu thập dữ liệu (Search, Web Scrape...).
- **Background Worker (Celery)**: Hệ thống tác vụ nền chạy bất đồng bộ để xử lý tài liệu, nhúng vector và tạo chỉ mục (indexing).

---

## 2. Use Case Diagram Tổng Quan

```mermaid
usecaseDiagram
actor User
actor "Owner / Admin" as Admin
actor "Deep Agent (AI)" as AI
actor "Background Worker" as Worker

User <|-- Admin

rectangle "NFD - SurfSense System" {
    usecase "Đăng nhập & Xác thực" as UC_Auth
    usecase "Quản lý Search Space" as UC_Space
    usecase "Tải lên tài liệu (Upload)" as UC_Upload
    usecase "Thiết lập Connector (Obsidian, Drive...)" as UC_Connector
    usecase "Chat với Deep Agent" as UC_Chat
    usecase "Cấu hình LLM" as UC_LLM
    usecase "Phân tích và Indexing (RAG)" as UC_Indexing
}

User --> UC_Auth
User --> UC_Upload
User --> UC_Chat
Admin --> UC_Space
Admin --> UC_Connector
Admin --> UC_LLM

Worker --> UC_Indexing
UC_Upload ..> UC_Indexing : <<include>>
UC_Connector ..> UC_Indexing : <<include>>

AI --> UC_Chat : Tham gia hội thoại
```

---

## 3. Use Case Diagram Phân Rã

### Phân rã: Quản lý và Phân tích Tài liệu (Thay thế cho luồng Phân tích ảnh X-quang)

> **Ghi chú**: Chức năng "Phân tích ảnh X-quang" không tìm thấy trong source. Dưới đây là phân rã chức năng tương đương của hệ thống: **Tải lên và xử lý tri thức (Document Processing Pipeline)**.

```mermaid
usecaseDiagram
actor User
actor "Background Worker" as Worker

rectangle "Xử lý Tri Thức (Knowledge Processing)" {
    usecase "Tải tài liệu / Lưu trang web" as UC_AddDoc
    usecase "Trích xuất văn bản (Parsing)" as UC_Parse
    usecase "Phân mảnh văn bản (Chunking)" as UC_Chunk
    usecase "Tạo Vector (Embedding)" as UC_Embed
    usecase "Lưu trữ Vector & Metadata" as UC_Save
}

User --> UC_AddDoc
UC_AddDoc ..> UC_Parse : <<include>>
Worker --> UC_Parse
Worker --> UC_Chunk
Worker --> UC_Embed
Worker --> UC_Save

UC_Parse ..> UC_Chunk : <<include>>
UC_Chunk ..> UC_Embed : <<include>>
UC_Embed ..> UC_Save : <<include>>
```

### Phân rã: Truy vấn & Chat AI (Deep Agent)

```mermaid
usecaseDiagram
actor User
actor "Deep Agent (AI)" as AI

rectangle "Tương tác AI (Chat & RAG)" {
    usecase "Gửi câu hỏi" as UC_Ask
    usecase "Phân tích câu hỏi (Reasoning)" as UC_Reason
    usecase "Tìm kiếm ngữ cảnh (Hybrid Search)" as UC_Search
    usecase "Sinh câu trả lời (LLM Generation)" as UC_Gen
    usecase "Stream kết quả (SSE)" as UC_Stream
}

User --> UC_Ask
UC_Ask ..> UC_Reason : <<include>>
AI --> UC_Reason
AI --> UC_Search
AI --> UC_Gen
AI --> UC_Stream

UC_Reason ..> UC_Search : <<include>>
UC_Search ..> UC_Gen : <<include>>
UC_Gen ..> UC_Stream : <<include>>
```

---

## 4. Đặc tả Use Case

### 4.1. Tải lên tài liệu (Upload Document)
- **Tên**: Tải lên tài liệu mới
- **Actor**: User
- **Mô tả**: Người dùng tải một hoặc nhiều file tài liệu lên hệ thống để hệ thống tạo chỉ mục (index) và lưu trữ.
- **Tiền điều kiện**: Người dùng đã đăng nhập và có quyền `DOCUMENTS_CREATE` trong Search Space đang chọn.
- **Hậu điều kiện**: Tài liệu được đưa vào hàng đợi (queue) để Background Worker xử lý, trạng thái hiển thị là "Pending".
- **Luồng chính**:
  1. Người dùng chọn chức năng Tải tài liệu trên giao diện web.
  2. Hệ thống kiểm tra dung lượng và số lượng giới hạn.
  3. Người dùng chọn file và xác nhận.
  4. Hệ thống tải file lên server, tạo bản ghi `Document` với trạng thái `Pending`.
  5. Hệ thống gửi task vào hàng đợi Celery (Redis Broker).
  6. Giao diện thông báo thành công và chờ xử lý.
- **Luồng ngoại lệ**:
  - File vượt quá kích thước cho phép -> Thông báo lỗi và từ chối xử lý.
  - Định dạng file không hỗ trợ -> Thông báo lỗi định dạng.

### 4.2. Trích xuất và Indexing (Background Processing)
- **Tên**: Xử lý và tạo chỉ mục tài liệu
- **Actor**: Background Worker
- **Mô tả**: Hệ thống worker tự động lấy tài liệu từ hàng đợi để trích xuất văn bản, chunking và embedding vào CSDL Vector.
- **Tiền điều kiện**: Có task pending trong hàng đợi Celery.
- **Hậu điều kiện**: Trạng thái tài liệu chuyển sang `Ready` (hoặc `Failed`). Dữ liệu Vector đã lưu vào pgvector.
- **Luồng chính**:
  1. Worker lấy task từ Redis broker.
  2. Đổi trạng thái Document thành `Processing`.
  3. Worker dùng Unstructured / Docling để trích xuất nội dung văn bản thuần từ file gốc.
  4. Dùng Chonkie để chia nhỏ văn bản thành các chunks.
  5. Gọi API LiteLLM Embedding để sinh vector cho các chunk.
  6. Lưu Chunks và Vectors vào database PostgreSQL (pgvector).
  7. Đổi trạng thái thành `Ready` và bắn tín hiệu (realtime sync qua ElectricSQL) báo cho UI.
- **Luồng ngoại lệ**:
  - Quá hạn API giới hạn LLM -> Đổi trạng thái thành `Failed` kèm theo lý do lỗi.
  - File không trích xuất được text (ảnh mờ/hỏng) -> Lưu `Failed` và log lại lỗi.

### 4.3. Chat với Deep Agent (Hybrid RAG)
- **Tên**: Chat hỏi đáp tài liệu
- **Actor**: User, Deep Agent
- **Mô tả**: Người dùng đặt câu hỏi trong một Thread (luồng hội thoại) và nhận lại phản hồi theo thời gian thực từ AI Agent.
- **Tiền điều kiện**: Người dùng đã đăng nhập, ở trong Search Space hợp lệ, có quyền `CHATS_CREATE`.
- **Hậu điều kiện**: Câu trả lời của AI và danh sách tài liệu tham khảo (Citations) hiển thị trên màn hình, lưu lại lịch sử hội thoại.
- **Luồng chính**:
  1. Người dùng gõ câu hỏi và nhấn gửi.
  2. Frontend gửi API `POST /api/v1/new_chat`.
  3. Backend khởi tạo state checkpointer và gọi Deep Agent (LangGraph).
  4. Deep Agent phân tích ý định (reasoning step).
  5. Deep Agent quyết định gọi tool Tìm kiếm tri thức (Hybrid Retrieval Service).
  6. Hệ thống thực hiện tìm Dense + Sparse và RRF, trả về top chunks liên quan.
  7. Deep Agent tổng hợp câu trả lời dựa trên chunks ngữ cảnh.
  8. Hệ thống đẩy Stream Event (SSE) về UI (text-delta, tool-output, done).
  9. Frontend render kết quả mượt mà và lưu database tin nhắn.
- **Luồng ngoại lệ**:
  - LLM Provider bị sập -> Trả về lỗi stream, thông báo AI gặp trục trặc.
  - Người dùng hỏi ngoài phạm vi tài liệu -> AI trả lời dựa trên hiểu biết chung hoặc báo không tìm thấy thông tin nếu prompt yêu cầu khắt khe.
