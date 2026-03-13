# Enterprise Knowledge Base Bot

## 📖 Overview / Mô tả

**English:**
Enterprise Knowledge Base Bot is a Retrieval-Augmented Generation (RAG) system built on FastAPI, ChromaDB, LangChain, and language model APIs. The system processes documents, generates vector embeddings, and provides context-aware responses to user queries.

**Tiếng Việt:**
Enterprise Knowledge Base Bot là một hệ thống Retrieval-Augmented Generation (RAG) được xây dựng trên FastAPI, ChromaDB, LangChain và các API mô hình ngôn ngữ. Hệ thống hỗ trợ phân tích, xử lý tài liệu, tạo embeddings vector và trả lời các câu hỏi dựa trên ngữ cảnh nội dung đã lưu trữ.

---

## 🎯 Key Features / Tính năng chính

| Feature | English | Tiếng Việt |
|---------|---------|-----------|
| 📄 Document Ingestion | Upload and process documents (TXT, PDF, DOCX) | Tải lên và xử lý tài liệu (TXT, PDF, DOCX) |
| 🔄 Vector Storage | Store embeddings in ChromaDB vector database | Lưu trữ vector embeddings trong ChromaDB |
| 🤖 Semantic Search | Context-aware retrieval using semantic search | Tìm kiếm ngữ cảnh dựa trên similarity |
| 💬 RAG Chat | Answer questions using retrieved documents | Trả lời câu hỏi với context từ knowledge base |
| ✅ Health Monitoring | Continuous health status monitoring | Kiểm tra trạng thái hệ thống liên tục |

---

## 🛠️ Tech Stack / Công nghệ

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | Latest |
| Vector Database | ChromaDB | Latest |
| Embeddings | HuggingFace Transformers | all-MiniLM-L6-v2 |
| LLM Framework | LangChain | Latest |
| Language Model | OpenAI-compatible (Mistral) | Mistral-7B-Instruct-v0.3 |
| Containerization | Docker Compose | 3.8 |
| Server | Uvicorn | Latest |
| Environment | python-dotenv | Latest |

---

## 📁 Project Structure / Cấu trúc dự án

```
enterprise-knowledge-bot/
├── app/                              # Application source code
│   ├── api/                          # API endpoints module
│   │   └── __init__.py
│   ├── core/                         # Core configuration
│   │   ├── __init__.py
│   │   └── config.py                 # Environment settings
│   ├── services/                     # Business logic
│   │   ├── __init__.py
│   │   └── rag_service.py            # RAG pipeline implementation
│   └── main.py                       # FastAPI application entry point
│
├── data/                             # Document storage
│   ├── .gitkeep
│   └── sample.txt                    # Sample test document
│
├── chroma_data/                      # ChromaDB persistent storage
│   ├── chroma.sqlite3                # Vector database file
│   └── collections/                  # Collection metadata
│
├── notebooks/                        # Jupyter notebooks
│   └── .gitkeep
│
├── Dockerfile                        # Container build configuration
├── docker-compose.yml                # Orchestration configuration
├── .dockerignore                     # Docker build exclusions
├── .gitignore                        # Git exclusions
├── .env.example                      # Environment template
├── requirements.txt                  # Python dependencies
├── LICENSE                           # Project license
└── README.md                         # Documentation

```

---

## 🚀 Installation & Setup / Thiết lập & Cài đặt

### Prerequisites / Yêu cầu tiên quyết

- Python 3.11+
- Docker & Docker Compose
- HuggingFace API Token
- 8GB RAM (recommended)

### Local Installation / Cài đặt local

```bash
# Clone repository
git clone https://github.com/VThanhNguyen2002/enterprise-knowledge-bot.git
cd enterprise-knowledge-bot

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with required API keys
```

### Environment Configuration / Cấu hình biến môi trường

Required environment variables in `.env`:

```env
# Required API credentials
HUGGINGFACEHUB_API_TOKEN=your_hf_token_here

# Model configuration (defaults provided)
EMBEDDING_MODEL=all-MiniLM-L6-v2
LLM_MODEL=mistralai/Mistral-7B-Instruct-v0.3

# System settings
CHROMA_PATH=./chroma_data
CHUNK_SIZE=500
CHUNK_OVERLAP=50
RETRIEVER_K=2
LLM_TEMPERATURE=0.1
```

**Security Notice:** Do NOT commit `.env` to Git. Use `.env.example` as template only.

---

## ⚙️ Running the Application / Chạy ứng dụng

### Method 1: Direct Execution / Chạy thủ công

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API available at: `http://localhost:8000`

### Method 2: Docker Compose / Chạy với Docker

```bash
# Build and start containers
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f backend

# Stop containers
docker-compose down
```

**Service Endpoints:**
- Backend API: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs` (Swagger UI)
- Alternative Docs: `http://localhost:8000/redoc` (ReDoc)

### Container Resource Configuration

From `docker-compose.yml`:
- **Memory limit:** 6GB (2GB reserved for OS)
- **CPU limit:** 2 cores
- **Health check:** Every 30 seconds with 10-second timeout

---

## 📡 API Endpoints / Các endpoints API

### Health & Status Endpoints

| Method | Endpoint | English | Tiếng Việt |
|--------|----------|---------|-----------|
| GET | `/` | Service status check | Kiểm tra trạng thái dịch vụ |
| GET | `/health` | Health check endpoint | Endpoint kiểm tra sức khỏe |

**Response:**
```json
{
  "status": "healthy"
}
```

### Document Processing / Xử lý tài liệu

| Method | Endpoint | English | Tiếng Việt |
|--------|----------|---------|-----------|
| POST | `/upload-test/` | Ingest sample document | Xử lý tài liệu mẫu |

**Request:** None (uses `data/sample.txt`)

**Response:**
```json
{
  "status": "success",
  "message": "Successfully processed N chunks from data/sample.txt"
}
```

### Chat & Retrieval / Hỏi-đáp & Truy xuất

| Method | Endpoint | English | Tiếng Việt |
|--------|----------|---------|-----------|
| POST | `/chat/` | RAG-based Q&A | Trả lời dựa trên RAG |

**Request Body:**
```json
{
  "question": "What are working hours?"
}
```

**Response:**
```json
{
  "status": "success",
  "question": "What are working hours?",
  "answer": "Working hours are 8 AM to 5 PM at the Hanoi headquarters..."
}
```

---

## 🔍 API Testing / Kiểm tra API

### Using curl

```bash
# Health check
curl http://localhost:8000/health

# Status check
curl http://localhost:8000/

# Ingest sample document
curl -X POST http://localhost:8000/upload-test/

# Chat query
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What are working hours?"}'
```

### Using FastAPI Interactive Documentation

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## ⚙️ Configuration Parameters / Các tham số cấu hình

### Vector Embedding Settings / Cấu hình Vector

| Parameter | Default | Purpose | Mục đích |
|-----------|---------|---------|---------|
| `EMBEDDING_MODEL` | all-MiniLM-L6-v2 | HuggingFace embedding model | Mô hình embedding |
| `CHUNK_SIZE` | 500 | Characters per document chunk | Ký tự trên mỗi đoạn |
| `CHUNK_OVERLAP` | 50 | Overlap between chunks | Chồng lấp giữa các đoạn |

### RAG Retrieval Settings / Cấu hình RAG

| Parameter | Default | Purpose | Mục đích |
|-----------|---------|---------|---------|
| `RETRIEVER_K` | 2 | Number of context documents | Số tài liệu lấy |
| `LLM_TEMPERATURE` | 0.1 | Response randomness (0=deterministic) | Tính ngẫu nhiên (0=cố định) |

### Performance Tuning / Tối ưu hiệu suất

- **Uvicorn Workers:** 2 workers (optimized for 2-core systems)
- **Health Check Interval:** 30 seconds
- **Request Timeout:** 10 seconds

---

## 🔐 Security / Bảo mật

### Credentials Management
- API keys stored in `.env` (excluded from Git via `.gitignore`)
- HuggingFace Router API for LLM access
- No hardcoded credentials in source code

### Input Validation
- File path validation in document ingestion
- File type restrictions (.txt format enforced)
- Question string validation in chat endpoint

### Container Security
- Non-root user execution (inherited from python:3.11-slim)
- Resource limits enforced (memory & CPU)
- Minimal base image

---

## 📝 Changelog / Nhật ký thay đổi

### v1.0.0 (Initial Release)
- RAG pipeline implementation
- Document ingestion via `/upload-test/`
- Chat endpoint with context-aware responses
- ChromaDB vector storage
- Docker containerization
- FastAPI OpenAPI documentation

---

## 🤝 Contributing / Đóng góp

Contributions welcome. Process:
1. Create feature branch: `git checkout -b feature/your-feature`
2. Commit changes: `git commit -am 'Add feature'`
3. Push to branch: `git push origin feature/your-feature`
4. Submit pull request

---

## 📄 License / Giấy phép

Licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

**Last Updated:** March 5, 2026  
**Status:** Stable v1.0.0  
**Maintained By:** Development Team
