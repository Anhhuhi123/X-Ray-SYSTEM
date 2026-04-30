# SurfSense Source Flow Summary

Tài liệu này tóm tắt luồng hoạt động chính của codebase SurfSense (web + backend + extension) theo góc nhìn runtime.

## 1) Kiến trúc tổng thể

Hệ thống gồm 3 phần chính:

- Web app Next.js: giao diện người dùng, gọi API backend, nhận stream trả lời theo SSE.
- Backend FastAPI: auth, RBAC, quản lý search space, connectors, documents, chat stream.
- Celery worker + beat: xử lý bất đồng bộ cho indexing, file processing, podcast, reindex, cleanup.

Hạ tầng runtime đi kèm (trong local/dev compose):

- PostgreSQL + pgvector: lưu dữ liệu nghiệp vụ, embeddings, chunks.
- Redis: broker/result backend cho Celery + rate limit + heartbeat tracking.
- ElectricSQL: realtime sync cho trạng thái UI (đặc biệt notifications/document status).

## 2) Điểm vào ứng dụng

Backend:

- Entry script: nbd_backend/main.py
- App factory/lifespan: nbd_backend/app/app.py

Khi backend khởi động, lifespan chạy các bước chính:

1. Tạo/check DB schema + bảng checkpointer.
2. Khởi tạo LLM router và image router.
3. Seed tài liệu SurfSense docs (timeout có guard).
4. Gắn middleware (perf log, slowapi, proxy headers, CORS).
5. Mount auth routes + toàn bộ API routes dưới prefix /api/v1.

Celery:

- Entry: nbd_backend/celery_worker.py
- Config: nbd_backend/app/celery_app.py

Celery tách queue:

- Queue mặc định: tác vụ user-facing (file, podcast, reindex, v.v.).
- Queue connectors: tác vụ index connector dài (Slack/Notion/Jira/Drive...).

Beat chạy định kỳ:

- check_periodic_schedules
- cleanup_stale_indexing_notifications

Web:

- Next layout/root providers: surfsense_web/app/layout.tsx
- API client wrapper: surfsense_web/lib/apis/base-api.service.ts

## 3) Luồng Auth và phân quyền

Auth trong backend dùng FastAPI Users + JWT + OAuth routes.

- Login/register/reset/verify được bảo vệ bằng rate limit theo IP.
- Middleware auth phía frontend tự gắn Bearer token.
- Khi token hết hạn, frontend thử refresh token tự động rồi retry request.

Phân quyền nghiệp vụ:

- Hầu hết endpoint quan trọng đều check RBAC qua check_permission.
- Quyền theo search space (READ/CREATE/UPDATE/DELETE cho chats/docs/connectors...).
- Với chat còn có check thread visibility (PRIVATE vs SEARCH_SPACE).

## 4) Luồng dữ liệu cốt lõi

### 4.1 Search Space và Connector

Flow quản lý connector nằm ở:

- nbd_backend/app/routes/search_source_connectors_routes.py

Luồng cơ bản:

1. User tạo connector trong 1 search space.
2. Backend validate config + check duplicate rule theo connector type.
3. Nếu periodic indexing bật, backend tạo lịch (meta scheduler).
4. User bấm Index Now hoặc scheduler kích hoạt.
5. Backend enqueue Celery task tương ứng connector type.
6. Worker index dữ liệu nguồn ngoài, chuẩn hóa thành Document + Chunk + embedding.
7. Cập nhật notification + last_indexed_at + trạng thái liên quan.

### 4.2 Upload file/document

Flow documents ở:

- nbd_backend/app/routes/documents_routes.py
- nbd_backend/app/tasks/celery_tasks/document_tasks.py

Luồng upload file:

1. Web upload nhiều file lên endpoint /api/v1/documents/fileupload.
2. Backend kiểm tra quota số lượng/size file.
3. Tạo trước Document với trạng thái pending (để UI thấy ngay).
4. Dispatch Celery task cho từng file.
5. Worker chạy pipeline parse/chunk/embed/index.
6. Trạng thái đổi pending -> processing -> ready/failed.

Flow extension/youtube tương tự: enqueue task riêng theo loại dữ liệu.

## 5) Luồng chat realtime

Route chat chính:

- nbd_backend/app/routes/new_chat_routes.py
- stream engine: nbd_backend/app/tasks/chat/stream_new_chat.py

### 5.1 Thread lifecycle

- List/create/update/delete thread qua các endpoint /threads.
- Thread có visibility:
  - PRIVATE: chỉ creator truy cập.
  - SEARCH_SPACE: thành viên search space có quyền phù hợp truy cập.

### 5.2 Gửi câu hỏi mới

Endpoint:

- POST /api/v1/new_chat

Luồng:

1. Frontend gửi user_query + chat_id + search_space_id + message history + mentioned docs.
2. Backend check permission + check thread access.
3. Lấy cấu hình model theo search space (agent_llm_id).
4. Trả StreamingResponse dạng text/event-stream.
5. stream_new_chat tạo deep agent, đọc context (docs được mention, connector availability, tools enabled/disabled).
6. Agent chạy tool calls + reasoning + sinh text.
7. Event được format theo Vercel AI SDK stream protocol và gửi dần về UI.

Các loại stream event chính:

- text-start, text-delta, text-end
- tool-input-start, tool-input-available
- tool-output-available
- data-thinking-step
- data-thread-title-update
- error / done

### 5.3 Regenerate và Resume

- Regenerate: rewind theo checkpoint trước khi câu trả lời cuối được tạo, stream lại, rồi cleanup message cũ.
- Resume: tiếp tục nhánh chat đang bị interrupt với decisions từ client.

## 6) Cơ chế retrieval và tìm kiếm

Service chính:

- nbd_backend/app/services/connector_service.py

Cách retrieval:

1. Hybrid search ở mức chunk.
2. Hybrid search ở mức document.
3. Hợp nhất bằng RRF (Reciprocal Rank Fusion) theo document-level.
4. Trả về kết quả có chunk id để phục vụ citation.

Mục tiêu: cân bằng semantic match + keyword match + chất lượng citation.

## 7) Deep Agent và Tooling

Factory agent:

- nbd_backend/app/agents/new_chat/chat_deepagent.py

Agent được dựng từ:

- LLM config (global YAML hoặc NewLLMConfig trong DB).
- Tool registry (search knowledge base, scrape web, podcast/report/image, memory, sandbox execute...).
- Checkpointer để giữ state conversation.

Tool availability phụ thuộc:

- connector loại nào đang có trong search space
- user bật/tắt tool từ UI
- cấu hình thread/sandbox

## 8) Frontend gọi backend như thế nào

API layer:

- surfsense_web/lib/apis/base-api.service.ts
- nhiều service con trong surfsense_web/lib/apis/

Mẫu chung:

1. Gọi endpoint backend qua NEXT_PUBLIC_FASTAPI_BACKEND_URL.
2. Auto thêm Authorization Bearer.
3. Khi 401 -> gọi refresh token -> retry 1 lần.
4. Chuẩn hóa lỗi AppError/AuthError cho UI.

Màn hình chat mới:

- surfsense_web/app/dashboard/[search_space_id]/new-chat/[[...chat_id]]/page.tsx

Trang này:

- gửi request chat
- đọc SSE stream
- map event thành message parts/tool cards/thinking steps
- cập nhật thread title và trạng thái realtime

## 9) Browser extension flow

Extension package:

- surfsense_browser_extension

Luồng tổng quát:

1. Extension thu thập/nén nội dung trang và metadata.
2. Gọi backend URL (mặc định domain production, có thể override local).
3. Backend nhận và đưa vào pipeline document EXTENSION.
4. Dữ liệu được index để chat có thể truy xuất sau đó.

## 10) Tóm tắt end-to-end (ngắn)

1. User tạo search space.
2. User kết nối connector hoặc upload tài liệu.
3. Backend enqueue Celery để index.
4. Worker tạo Document/Chunk/Embedding vào Postgres + pgvector.
5. User chat ở UI.
6. Backend deep-agent gọi retrieval/tooling.
7. Kết quả stream SSE về UI theo từng chunk/tool event.
8. UI render text + citations + tool outputs realtime.

## 11) File quan trọng nên đọc tiếp

- Backend entry/lifecycle: nbd_backend/main.py, nbd_backend/app/app.py
- Chat routes: nbd_backend/app/routes/new_chat_routes.py
- Chat stream core: nbd_backend/app/tasks/chat/stream_new_chat.py
- Connectors routes: nbd_backend/app/routes/search_source_connectors_routes.py
- Connector retrieval service: nbd_backend/app/services/connector_service.py
- Celery config: nbd_backend/app/celery_app.py
- Document tasks: nbd_backend/app/tasks/celery_tasks/document_tasks.py
- Frontend chat page: surfsense_web/app/dashboard/[search_space_id]/new-chat/[[...chat_id]]/page.tsx
- Frontend API base: surfsense_web/lib/apis/base-api.service.ts
- Extension backend URL config: surfsense_browser_extension/utils/backend-url.ts
