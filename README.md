# 🤖 Enterprise Knowledge Bot

> **Ask your company documents anything — instantly, securely, and with full conversation memory.**
>
> A production-grade RAG chatbot built with FastAPI, LangChain, ChromaDB & Groq. Designed for enterprise internal knowledge retrieval with advanced query reformulation and multi-layer security guardrails.

---

## ⚡ Key Features

| Feature | Description |
|---|---|
| 🔍 **Advanced RAG + Query Reformulation** | Follow-up questions with pronouns ("What does *it* say?") are automatically rewritten into standalone queries before hitting the vector DB — eliminating context-blind retrieval |
| 🛡️ **Multi-layer Security** | Unicode-normalized injection detection, data-poison scanning on every upload, history content validation, and hardened system prompts |
| 🚀 **High-Performance Inference** | Groq API (llama-3.3-70b) for sub-second LLM responses + HuggingFace model pre-warmed at startup (zero cold-start) |
| 💬 **Stateful Multi-turn Chat** | Full conversation history preserved in Streamlit session state and forwarded to the backend on every request |
| 🔒 **DevSecOps Ready** | Rate limiting (slowapi), security headers (HSTS, X-Frame-Options, nosniff), restricted CORS, token redaction in logs |
| 🐳 **One-command Deployment** | `docker compose up --build` — fully orchestrated with persistent ChromaDB volume |

---

## 🏆 Tech Stack

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-0.2+-1C3C3C?style=for-the-badge)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-orange?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│              Streamlit (port 8501) — ekb-frontend               │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP (internal Docker network)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FastAPI BACKEND                           │
│                    Uvicorn (port 8000) — ekb-backend            │
│                                                                 │
│  POST /upload/              POST /chat/                         │
│  ┌────────────────┐        ┌─────────────────────────────────┐  │
│  │ 1. Validate    │        │  1. Validate question + history │  │
│  │ 2. Poison scan │        │  2. Serialize history → text    │  │
│  │ 3. Chunk text  │        │  3. ── QUERY REFORMULATION ──   │  │
│  │ 4. Embed       │        │     LLM rewrites follow-ups     │  │
│  │    (HuggingFace│        │     into standalone questions   │  │
│  │    offline)    │        │  4. ChromaDB retrieval (k=2)    │  │
│  │ 5. Store →     │        │  5. LLM answer (Groq)           │  │
│  │   ChromaDB     │        └─────────────────────────────────┘  │
│  └────────────────┘                                             │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
              ┌─────▼──────┐          ┌───────▼──────┐
              │  ChromaDB  │          │  Groq API    │
              │  (Volume)  │          │  llama-3.3-  │
              │  chroma_   │          │  70b-vers.   │
              │  data/     │          └──────────────┘
              └────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose installed
- A [Groq API key](https://console.groq.com/)

### 1. Clone & Configure

```bash
git clone https://github.com/your-username/enterprise-knowledge-bot.git
cd enterprise-knowledge-bot

# Create your environment file
cp .env.example .env
# Edit .env — set your GROQ_API_KEY
```

### 2. Launch (One Command)

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| 🌐 Chat UI | http://localhost:8501 |
| ⚙️ API Docs | http://localhost:8000/docs |
| ❤️ Health | http://localhost:8000/health |

> **First build takes ~3-5 min** — the `all-MiniLM-L6-v2` model (~90 MB) is downloaded and cached inside the image. Subsequent starts are instant.

### 3. Usage

1. Open **http://localhost:8501**
2. Upload a `.txt` knowledge file via the sidebar (max 5 MB)
3. Ask questions in the chat — the bot answers from your document

---

## 🔧 Local Development (Without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Terminal 1 — Backend
PYTHONPATH=. python3 -m uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
PYTHONPATH=. python3 -m streamlit run app_ui/main_app.py
```

---

## 🧠 Behind the Scenes — Solving "Context-Blind Retrieval"

### The Problem
In a multi-turn conversation, users naturally ask follow-up questions with pronouns:

> *User:* "What are the company's IT security policies?"
> *User:* **"What technologies does it mention?"**

A naive RAG system sends `"What technologies does it mention?"` directly to the vector database. The embedding of this pronoun-heavy query matches nothing — returning empty context and causing the LLM to say *"I cannot find this information."*

### The Solution — Query Reformulation
Before hitting the vector DB, we insert an LLM-powered **condensation step**:

```
History + Follow-up question
         │
         ▼
    LLM (Groq): "Rewrite as a standalone question"
         │
         ▼
"What technologies does the IT security policy document mention?"
         │
         ▼
    ChromaDB retrieval  ← Now finds the right chunks
         │
         ▼
    LLM answer using original phrasing
```

This runs **only when history exists** (skipped on first turn to save latency) and has a **fallback** to the raw question if the reformulation call fails.

---

## 🛡️ Security Architecture

| Layer | Mechanism |
|---|---|
| Input validation | `unicodedata.normalize("NFKC")` + 10 regex patterns on question & history |
| Data poisoning | 11 regex patterns scan every uploaded document chunk before ingestion |
| Rate limiting | `slowapi`: 2 uploads/min, 5 chats/min per IP |
| HTTP headers | HSTS, X-Frame-Options: DENY, X-Content-Type-Options: nosniff |
| CORS | Restricted to `ALLOWED_ORIGINS` env var (default: localhost:8501 only) |
| Log safety | API tokens redacted via regex before any log output |

---

## 📁 Project Structure

```
enterprise-knowledge-bot/
├── app/                        # FastAPI backend (Clean Architecture)
│   ├── api/routers/            # upload.py, chat.py, health.py
│   ├── core/                   # config.py, limiter.py
│   ├── schemas/request.py      # ChatMessage, QuestionRequest + validators
│   ├── services/rag_service.py # Core RAG pipeline
│   └── main.py                 # App factory + security middleware
├── app_ui/                     # Streamlit frontend
│   ├── api_client.py           # HTTP client for backend
│   ├── components.py           # Sidebar, chat display, chat input
│   └── main_app.py             # Entry point + session state
├── Dockerfile                  # Backend image (model pre-cached at build)
├── Dockerfile.frontend         # Frontend image
├── docker-compose.yml          # Full orchestration
├── requirements.txt            # All dependencies
└── .env.example                # Environment variable template
```

---

## 📄 License

MIT © 2025

---
---

# 🇻🇳 Phiên bản Tiếng Việt

> **Hỏi bất kỳ điều gì về tài liệu của công ty bạn — tức thì, bảo mật, và nhớ toàn bộ cuộc hội thoại.**
>
> Một chatbot RAG cấp production được xây dựng bằng FastAPI, LangChain, ChromaDB & Groq. Được thiết kế cho hệ thống truy xuất tri thức nội bộ doanh nghiệp với cơ chế tái diễn đạt câu hỏi nâng cao và nhiều lớp bảo mật.

---

## ⚡ Tính Năng Nổi Bật

| Tính năng | Mô tả |
|---|---|
| 🔍 **RAG Nâng cao + Tái Diễn Đạt Câu Hỏi** | Các câu hỏi tiếp nối dùng đại từ ("Nó đề cập đến gì?") được LLM tự động viết lại thành câu hỏi độc lập trước khi tìm kiếm trong Vector DB — giải quyết hoàn toàn vấn đề "mù ngữ cảnh" |
| 🛡️ **Bảo Mật Đa Lớp** | Phát hiện tấn công injection chuẩn hóa Unicode, quét độc nội dung mỗi lần upload, xác thực lịch sử hội thoại, và system prompt được gia cố chống rò rỉ |
| 🚀 **Hiệu Năng Cao** | Groq API (llama-3.3-70b) cho tốc độ suy luận dưới 1 giây + mô hình HuggingFace được nạp sẵn khi khởi động (không có độ trễ cold-start) |
| 💬 **Chat Đa Lượt Nhớ Lịch Sử** | Toàn bộ lịch sử hội thoại được lưu trong session state của Streamlit và truyền đến backend trong mỗi request |
| 🔒 **DevSecOps Sẵn Sàng** | Giới hạn tốc độ request (slowapi), header bảo mật (HSTS, X-Frame-Options, nosniff), CORS hạn chế, token API được che trong log |
| 🐳 **Triển Khai Một Lệnh** | `docker compose up --build` — được orchestrate đầy đủ với volume ChromaDB lưu trữ lâu dài |

---

## 🏗️ Kiến Trúc Hệ Thống

```
[ Người dùng tải lên file .txt ]
         │
         ▼
  Streamlit UI (port 8501)
  ─ Gửi file → POST /upload/
         │
         ▼
  FastAPI Backend (port 8000)
  ─ Kiểm tra: chỉ .txt, tối đa 5MB
  ─ Quét độc nội dung (11 regex patterns)
  ─ Chia nhỏ văn bản (chunk 500 từ)
  ─ Embed bằng HuggingFace all-MiniLM-L6-v2 (offline)
  ─ Lưu vector → ChromaDB

─────────────────────────────────────────────

[ Người dùng đặt câu hỏi ]
         │
         ▼
  Streamlit UI → POST /chat/ (gửi kèm lịch sử hội thoại)
         │
         ▼
  FastAPI: Xác thực câu hỏi + lịch sử (Unicode + regex)
         │
         ▼  (nếu có lịch sử hội thoại)
  ── TÁI DIỄN ĐẠT CÂU HỎI ──
  Groq LLM viết lại "Nó đề cập gì?" →
  "Tài liệu chính sách IT đề cập đến công nghệ nào?"
         │
         ▼
  ChromaDB: Tìm kiếm k=2 đoạn văn bản liên quan nhất
         │
         ▼
  Groq LLM (llama-3.3-70b): Tạo câu trả lời từ ngữ cảnh
         │
         ▼
  Streamlit: Hiển thị câu trả lời từng từ (typing effect)
```

---

## 🚀 Hướng Dẫn Chạy Nhanh

### Yêu Cầu
- Docker & Docker Compose đã cài đặt
- [Groq API key](https://console.groq.com/) (miễn phí)

### 1. Clone & Cấu Hình

```bash
git clone https://github.com/your-username/enterprise-knowledge-bot.git
cd enterprise-knowledge-bot

# Tạo file môi trường
cp .env.example .env
# Mở .env và điền GROQ_API_KEY của bạn
```

### 2. Khởi Chạy (Một lệnh duy nhất)

```bash
docker compose up --build
```

| Dịch vụ | Địa chỉ |
|---|---|
| 🌐 Giao diện Chat | http://localhost:8501 |
| ⚙️ Tài liệu API | http://localhost:8000/docs |
| ❤️ Kiểm tra sức khỏe | http://localhost:8000/health |

> **Lần build đầu mất ~3-5 phút** — mô hình `all-MiniLM-L6-v2` (~90 MB) được tải và cache bên trong image. Các lần khởi động sau là tức thì.

### 3. Sử Dụng

1. Mở **http://localhost:8501**
2. Tải lên file `.txt` qua thanh sidebar (tối đa 5 MB)
3. Đặt câu hỏi trong chat — bot trả lời dựa trên tài liệu của bạn

---

## 🧠 Giải Thích Kỹ Thuật — Giải Quyết "Mù Ngữ Cảnh"

### Vấn Đề
Trong hội thoại nhiều lượt, người dùng tự nhiên dùng đại từ khi hỏi tiếp:

> *Lượt 1:* "Chính sách bảo mật IT của công ty là gì?"
> *Lượt 2:* **"Nó đề cập đến những công nghệ nào?"**

Một hệ thống RAG đơn giản sẽ gửi chuỗi `"Nó đề cập đến những công nghệ nào?"` thẳng vào Vector Database. Vector embedding của câu này không khớp với bất kỳ đoạn văn nào → trả về ngữ cảnh rỗng → LLM nói *"Tôi không tìm thấy thông tin này."*

### Giải Pháp — Tái Diễn Đạt Câu Hỏi (Query Reformulation)
Trước khi truy xuất vector, chúng tôi chèn thêm một bước **ngưng tụ câu hỏi** bằng LLM:

| Bước | Nội dung |
|---|---|
| **Input** | Lịch sử hội thoại + câu hỏi tiếp nối |
| **LLM (Groq)** | "Hãy viết lại thành câu hỏi độc lập hoàn chỉnh" |
| **Output** | "Tài liệu chính sách bảo mật IT đề cập đến những công nghệ nào?" |
| **ChromaDB** | Tìm đúng đoạn văn bản liên quan |
| **LLM (Groq)** | Trả lời bằng giọng tự nhiên của người dùng |

**Tối ưu hiệu năng:**
- Bước này **chỉ chạy khi có lịch sử** (bỏ qua ở lượt hỏi đầu tiên → tiết kiệm ~300ms)
- Có **fallback tự động** về câu hỏi gốc nếu bước ngưng tụ bị lỗi

---

## 🛡️ Kiến Trúc Bảo Mật

| Lớp bảo vệ | Cơ chế |
|---|---|
| Xác thực đầu vào | `unicodedata.normalize("NFKC")` + 10 regex chặn injection (bao gồm cả biến thể Unicode) |
| Chống đầu độc dữ liệu | 11 regex quét từng đoạn tài liệu trước khi nhập vào ChromaDB |
| Giới hạn tốc độ | `slowapi`: 2 lần upload/phút, 5 câu chat/phút mỗi IP |
| Header HTTP | HSTS, X-Frame-Options: DENY, X-Content-Type-Options: nosniff |
| CORS | Chỉ cho phép origin từ biến `ALLOWED_ORIGINS` (mặc định: localhost:8501) |
| Log an toàn | Token API bị che tự động bằng regex trước khi ghi log |

---

## 💡 Giải Thích Thuật Ngữ Kỹ Thuật

| Thuật ngữ | Giải thích đơn giản |
|---|---|
| **RAG** (Retrieval-Augmented Generation) | Phương pháp kết hợp tìm kiếm tài liệu + AI tạo văn bản. Thay vì AI "đoán mò", nó tìm đúng đoạn văn bản liên quan rồi mới trả lời |
| **Query Reformulation** (Tái Diễn Đạt Câu Hỏi) | Bước dùng AI viết lại câu hỏi tiếp nối (dùng đại từ) thành câu hỏi độc lập hoàn chỉnh trước khi tìm kiếm |
| **Embeddings** (Vector Nhúng) | Biểu diễn văn bản dưới dạng con số (vector) để máy tính có thể đo độ tương đồng về ý nghĩa, không chỉ từ ngữ |
| **ChromaDB** | Cơ sở dữ liệu lưu trữ vector — cho phép tìm kiếm theo ý nghĩa ngữ nghĩa thay vì từ khóa chính xác |
| **LLM** (Large Language Model) | Mô hình ngôn ngữ lớn (ở đây là llama-3.3-70b chạy trên Groq) — phần trả lời câu hỏi của pipeline |
| **Cold-start latency** | Độ trễ lần đầu do phải tải mô hình AI vào bộ nhớ — được loại bỏ bằng cách tải sẵn khi build Docker image |
| **Data Poisoning** | Tấn công bằng cách upload tài liệu độc hại để làm lệch câu trả lời của AI |
| **Prompt Injection** | Tấn công trong đó người dùng cố ép AI bỏ qua các quy tắc bằng cách nhúng câu lệnh vào câu hỏi |

