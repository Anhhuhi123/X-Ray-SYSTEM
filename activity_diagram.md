# Activity Diagram (Sơ đồ Hoạt động)

## 1. Đăng nhập (Authentication)

```mermaid
activityDiagram
    %% Syntax Mermaid cho Activity/Flowchart
    graph TD
        Start((Start)) --> InputCredentials[Nhập Email và Mật khẩu]
        InputCredentials --> SendRequest[Gửi API POST /auth/jwt/login]
        SendRequest --> CheckLimit{Kiểm tra Rate Limit IP?}
        
        CheckLimit -- Bị khóa --> ErrorLimit[Trả về 429 Too Many Requests] --> End((End))
        CheckLimit -- An toàn --> VerifyCredentials{Xác thực thông tin?}
        
        VerifyCredentials -- Sai --> ErrorInvalid[Trả về lỗi 400 Bad Request] --> End
        VerifyCredentials -- Đúng --> GenerateJWT[Tạo Access Token JWT]
        
        GenerateJWT --> ReturnToken[Trả về Token cho Client]
        ReturnToken --> SaveToken[Client lưu Bearer Token]
        SaveToken --> End
```

---

## 2. Phân tích ảnh X-quang

> **Ghi chú**: Không tìm thấy trong source. Mã nguồn không có chức năng tải và phân tích ảnh X-quang. Dưới đây là Activity Diagram thay thế cho chức năng tương đương trong hệ thống: **Quy trình Tải lên và Phân tích Tài liệu (Document Processing)**.

```mermaid
graph TD
    Start((Start)) --> UploadReq[User gửi request Upload File]
    UploadReq --> CheckQuota{Kiểm tra Quota/Size?}
    
    CheckQuota -- Vượt mức --> RejectUpload[Từ chối Upload & Trả lỗi 413/400] --> End((End))
    CheckQuota -- Hợp lệ --> CreatePendingDoc[Tạo Document trạng thái Pending]
    
    CreatePendingDoc --> EnqueueCelery[Enqueue Celery Task]
    EnqueueCelery --> WorkerPick[Celery Worker nhận Task]
    WorkerPick --> Parsing[Trích xuất văn bản - Docling/Unstructured]
    
    Parsing --> Chunking[Phân mảnh văn bản - Chonkie]
    Chunking --> Embedding[Gọi LLM Embedding sinh Vector]
    
    Embedding --> DBUpdate[Lưu Vector & Chunks vào pgvector]
    DBUpdate --> ChangeStateReady[Cập nhật trạng thái thành Ready]
    ChangeStateReady --> End
```

---

## 3. Truy xuất tri thức y khoa (Điều chỉnh thành Truy xuất tri thức đa nguồn)

> **Ghi chú**: Hệ thống NFD hỗ trợ truy xuất tri thức tổng quát dựa trên tài liệu người dùng tải lên, không giới hạn trong phạm vi y khoa.

```mermaid
graph TD
    Start((Start)) --> SetupConnector[User cấu hình Search Connector]
    SetupConnector --> SaveConfig[Lưu cấu hình vào Database]
    SaveConfig --> ScheduleCheck{Có bật tự động đồng bộ?}
    
    ScheduleCheck -- Có --> CronJob[Tạo lịch chạy Celery Beat]
    ScheduleCheck -- Không --> WaitManual[Chờ kích hoạt thủ công]
    
    CronJob --> FetchData[Lấy dữ liệu từ nguồn ngoài \n Slack, Obsidian, Web]
    WaitManual --> FetchData
    
    FetchData --> CompareHash{Dữ liệu có thay đổi?}
    CompareHash -- Không --> SkipUpdate[Bỏ qua] --> End((End))
    CompareHash -- Có --> Processing[Chuyển qua luồng Phân tích & Indexing]
    
    Processing --> SyncStatus[Đồng bộ trạng thái UI qua ElectricSQL]
    SyncStatus --> End
```

---

## 4. Sinh giải thích bằng Hybrid RAG (Deep Agent Chat)

```mermaid
graph TD
    Start((Start)) --> ReceiveQuery[Nhận câu hỏi người dùng qua SSE Route]
    ReceiveQuery --> LoadState[Tải Checkpoint & Lịch sử hội thoại]
    LoadState --> InitAgent[Khởi tạo Deep Agent]
    
    InitAgent --> Reasoning{Agent suy luận có cần tìm kiếm?}
    
    Reasoning -- Không cần --> GenerateDirect[Sinh câu trả lời trực tiếp]
    Reasoning -- Cần --> CallRetrievalTool[Gọi Tool Tìm kiếm Tri thức]
    
    CallRetrievalTool --> SearchSpaceCheck[Xác định Search Space & Context]
    SearchSpaceCheck --> HybridQuery[Sinh Keywords & Vector từ Query]
    
    HybridQuery --> ParallelSearch((Trộn))
    ParallelSearch --> Dense[Dense Search\npgvector]
    ParallelSearch --> Sparse[Sparse Search\nFull Text]
    
    Dense --> MergeRRF[Chạy thuật toán Reciprocal Rank Fusion]
    Sparse --> MergeRRF
    
    MergeRRF --> ReturnChunks[Trả về danh sách Chunks tốt nhất]
    ReturnChunks --> AppendContext[Gắn Chunks vào Prompt Ngữ cảnh]
    
    AppendContext --> GenerateAnswer[LLM tạo sinh câu trả lời]
    GenerateDirect --> LLMStream[Stream SSE Chunk Text về Client]
    GenerateAnswer --> LLMStream
    
    LLMStream --> StreamDone{Hoàn thành?}
    StreamDone -- Chưa --> LLMStream
    StreamDone -- Rồi --> SaveMessage[Lưu tin nhắn vào CSDL]
    SaveMessage --> End((End))
```
