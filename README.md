# Enterprise Knowledge Base Bot

**Enterprise Knowledge Base Bot** là một hệ thống Retrieval-Augmented Generation (RAG) đơn giản được xây dựng bằng FastAPI, ChromaDB, LangChain và API của các mô hình ngôn ngữ. Dự án cho phép tải tài liệu, tạo vector embeddings, lưu trữ trong một vector database và trả lời câu hỏi dựa trên ngữ cảnh văn bản.

## 🎯 Tính năng chính

- Ingest tài liệu (PDF, TXT, DOCX...) và chia nhỏ thành từng đoạn.
- Sinh embedding với HuggingFace `all-MiniLM-L6-v2`. 
- Lưu trữ vectors trong ChromaDB cục bộ.
- Kết hợp với mô hình LLM qua chuẩn OpenAI API (qua Hugging Face Router).
- Endpoint `/chat` để gửi câu hỏi và nhận câu trả lời dựa trên ngữ cảnh.
- Kiểm tra sức khỏe qua `/health`.

## 🛠️ Tech Stack

- **Framework**: FastAPI
- **Database vector**: ChromaDB
- **Embeddings**: HuggingFace, LangChain
- **LLM**: Qwen/X (qua ChatOpenAI) hoặc khác tuỳ cấu hình
- **Workflow**: LangChain RAG
- **Containerization**: Docker, Docker Compose
- **Env management**: python-dotenv

## 📁 Cấu trúc thư mục

```
enterprise-knowledge-bot/
├── app/                      # Mã nguồn chính của ứng dụng
│   ├── api/                  # Chứa các endpoint của FastAPI (vd. /upload, /chat)
│   ├── core/                 # Cấu hình hệ thống, kết nối Vector DB, LLM config
│   ├── services/             # Logic xử lý RAG (Document loading, chunking, retrieval)
│   └── main.py               # File gốc khởi chạy ứng dụng FastAPI
├── data/                     # Thư mục chứa tài liệu test (PDF, TXT)
├── notebooks/                # Chứa file .ipynb để test nhanh các model và prompt
├── chroma_data/              # Json/SQLite data của ChromaDB (cố định dữ liệu)
├── .env.example              # File mẫu chứa các biến môi trường (API Keys)
├── .gitignore                # Bỏ qua các file không cần push (như .env, __pycache__)
├── Dockerfile                # Hướng dẫn build image cho backend
├── docker-compose.yml        # File orchestrate các dịch vụ (FastAPI + Vector DB)
└── requirements.txt          # Danh sách thư viện (FastAPI, LangChain, ChromaDB...)
```

## 🚀 Thiết lập môi trường nội bộ

1. **Clone repo**
   ```bash
   git clone https://github.com/VThanhNguyen2002/enterprise-knowledge-bot.git
   cd enterprise-knowledge-bot
   git checkout feature/init-main-server  # hoặc nhánh bạn đang làm việc
   ```

2. **Tạo virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate    # bash/zsh
   # hoặc: .venv\Scripts\activate (Windows)
   ```

3. **Cài đặt dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Cấu hình biến môi trường**
   - Copy file mẫu: `cp .env.example .env`
   - Mở `.env` và điền các khóa API (OpenAI, HUGGINGFACEHUB_API_TOKEN,...) và các tham số cấu hình.
   - Quan trọng: **KHÔNG** commit file `.env` vào Git.

5. **Chuẩn bị thư mục dữ liệu**
   - Tạo thư mục `data/` để chứa các tài liệu test.
   - Khi chạy container/ứng dụng, thư mục `chroma_data/` sẽ tự động tạo và lưu persist.

## ⚙️ Chạy server

### Chạy thủ công bằng Python
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Chạy qua Docker Compose
```bash
docker-compose up --build
```
- Backend: http://localhost:8000
- ChromaDB (port nội bộ 8001) cho debug/GUI.

## 📡 API Endpoints cơ bản

| Phương thức | Đường dẫn     | Mô tả                          |
|-------------|---------------|--------------------------------|
| GET         | `/`           | Kiểm tra dịch vụ đang chạy     |
| GET         | `/health`     | Health check                   |
| POST        | `/ingest`     | Upload file và tạo vector      |
| POST        | `/chat`       | Gửi câu hỏi RAG, nhận trả lời   |

> **Lưu ý**: Các route `/ingest`, `/chat` chưa được triển khai trong mã nguồn mẫu, bạn cần thêm router trong `app/api`.

## 📌 Lời khuyên phát triển

- Tách các thành phần `router`, `schemas`, `services` theo chuẩn Clean Architecture.  
- Luôn bật logging và bắt lỗi trong các định tuyến API.  
- Đảm bảo `.gitignore` loại trừ mọi dữ liệu nhạy cảm và tập tin lớn.

---
*README được viết bằng tiếng Việt nhằm hỗ trợ đội phát triển và các bên liên quan dễ tiếp cận dự án.*
