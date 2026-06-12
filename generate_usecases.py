import subprocess
import os

files = {
    "usecase_over.mmd": """flowchart LR
    User([User])
    Admin([Owner / Admin])
    AI([Deep Agent AI])
    Worker([Background Worker])

    User --- Admin

    subgraph NFD [NFD - SurfSense System]
        direction TB
        UC_Auth([Đăng nhập & Xác thực])
        UC_Space([Quản lý Search Space])
        UC_Upload([Tải lên tài liệu])
        UC_Connector([Thiết lập Connector])
        UC_Chat([Chat với Deep Agent])
        UC_LLM([Cấu hình LLM])
        UC_Indexing([Phân tích và Indexing])
    end

    User --> UC_Auth
    User --> UC_Upload
    User --> UC_Chat
    Admin --> UC_Space
    Admin --> UC_Connector
    Admin --> UC_LLM

    Worker --> UC_Indexing
    UC_Upload -.->|include| UC_Indexing
    UC_Connector -.->|include| UC_Indexing

    AI --> UC_Chat
""",
    "usecase_doc.mmd": """flowchart LR
    User([User])
    Worker([Background Worker])

    subgraph KP [Xử lý Tri Thức]
        direction TB
        UC_AddDoc([Tải tài liệu / Lưu trang web])
        UC_Parse([Trích xuất văn bản])
        UC_Chunk([Phân mảnh văn bản])
        UC_Embed([Tạo Vector])
        UC_Save([Lưu trữ Vector & Metadata])
    end

    User --> UC_AddDoc
    UC_AddDoc -.->|include| UC_Parse
    Worker --> UC_Parse
    Worker --> UC_Chunk
    Worker --> UC_Embed
    Worker --> UC_Save

    UC_Parse -.->|include| UC_Chunk
    UC_Chunk -.->|include| UC_Embed
    UC_Embed -.->|include| UC_Save
""",
    "usecase_chat.mmd": """flowchart LR
    User([User])
    AI([Deep Agent AI])

    subgraph TTAI [Tương tác AI Chat & RAG]
        direction TB
        UC_Ask([Gửi câu hỏi])
        UC_Reason([Phân tích câu hỏi])
        UC_Search([Tìm kiếm ngữ cảnh])
        UC_Gen([Sinh câu trả lời])
        UC_Stream([Stream kết quả])
    end

    User --> UC_Ask
    UC_Ask -.->|include| UC_Reason
    AI --> UC_Reason
    AI --> UC_Search
    AI --> UC_Gen
    AI --> UC_Stream

    UC_Reason -.->|include| UC_Search
    UC_Search -.->|include| UC_Gen
    UC_Gen -.->|include| UC_Stream
"""
}

for mmd_name, content in files.items():
    with open(mmd_name, "w", encoding="utf-8") as f:
        f.write(content)
        
    svg_name = mmd_name.replace(".mmd", ".svg")
    print(f"Generating {svg_name}...")
    subprocess.run(["npx", "@mermaid-js/mermaid-cli", "-i", mmd_name, "-o", f"Architecture/{svg_name}"], check=True)
    os.remove(mmd_name)

print("Finished generation process!")
