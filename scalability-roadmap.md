# 📈 Scalability & Security Roadmap

> **Current deployment**: Single-container monolith on Hugging Face Spaces (Free Tier), optimized for AI logic accuracy and zero infrastructure cost.
> **This document**: Maps the evolution path from the current demo to a full enterprise-grade, multi-tenant production system.

---

## Phase 1 — Async Ingestion (Completed ✅)

**Goal**: Decouple heavy embedding work from the HTTP request cycle.

| Component | Implementation |
|---|---|
| Task broker | Redis (AOF persistence, 256 MB cap) |
| Worker | Celery (`acks_late=True`, exponential back-off retry ×3) |
| Upload endpoint | Returns `202 Accepted` + `task_id` immediately |
| Cleanup | `try/finally` in worker — temp files always deleted |

> *Preserved in `docker-compose.yml` and `app/worker.py` for VPS deployment. Reverted to sync mode for free-tier HF Spaces.*

---

## Phase 2 — Vector DB Migration (Planned 🔵)

**Goal**: Replace ChromaDB (local file) with Qdrant for distributed, high-concurrency retrieval.

| Criteria | ChromaDB (Current) | Qdrant (Target) |
|---|---|---|
| Deployment | Embedded file | Standalone service / Qdrant Cloud |
| Concurrent reads | Limited | Async, multi-node |
| Metadata filtering | Basic | Rich payload filtering |
| Scalability | Single-node | Horizontal sharding |

**Migration steps**:
1. Add `qdrant-client` to `requirements.txt`
2. Replace `Chroma(...)` with `QdrantVectorStore(...)` in `rag_service.py`
3. Add `qdrant` service to `docker-compose.yml` with persistent volume
4. One-time re-ingestion of existing documents

---

## Phase 3 — Semantic Cache & Observability (Planned 🔵)

**Goal**: Eliminate redundant LLM calls for repeated questions; gain production visibility.

### 3A. Semantic Cache (Redis + Embedding Similarity)

```
User question → embed → cosine similarity check vs Redis cache
  ├─ Hit  (similarity > 0.95): return cached answer instantly (~5ms)
  └─ Miss: run full RAG pipeline → store result in Redis (TTL: 1h)
```

**Implementation**: `GPTCache` or custom middleware in `rag_service.chat()`.

### 3B. Observability Stack

| Tool | Purpose |
|---|---|
| Prometheus + Grafana | Request latency, token usage, cache hit rate |
| Sentry | Exception tracking with full stack traces |
| Structured JSON logs | Machine-parseable via `python-json-logger` |

---

## Phase 4 — Enterprise Security, Compliance & Data Isolation 🏢

**Goal**: Satisfy corporate security requirements (ISO 27001 / SOC 2) for multi-tenant, regulated environments.

> *Tóm tắt (VI): Giai đoạn này bổ sung các lớp bảo mật cấp doanh nghiệp: xác thực SSO, phân quyền dữ liệu theo vai trò, mã hóa, quét malware và nhật ký kiểm toán tuân thủ.*

---

### 4A. Identity & Access Management (IAM) — SSO / OIDC

**Problem**: The current demo has no user authentication. Any visitor can upload documents and query the system.

**Solution**: Integrate **OAuth2 / OpenID Connect (OIDC)** via a FastAPI middleware layer.

```
User browser
    │
    ▼ (unauthenticated)
Nginx / FastAPI Auth Middleware
    │  redirect to Identity Provider
    ▼
┌────────────────────────────────────┐
│  Identity Provider (IdP)           │
│  ─ Microsoft Entra ID (Azure AD)   │
│  ─ Okta Workforce Identity         │
│  ─ Google Workspace (GCIP)         │
└────────────────────────────────────┘
    │  returns JWT (id_token + access_token)
    ▼
FastAPI validates token → extracts user identity + groups
    │
    ▼
Request proceeds with user context attached
```

**Libraries**: `python-jose` (JWT validation), `authlib` (OAuth2 client), `fastapi-users`.

**Key fields extracted from OIDC token**:

| Claim | Usage |
|---|---|
| `sub` | Unique user ID for audit logs |
| `email` | Display name in UI |
| `groups` / `roles` | RBAC permission mapping (see §4B) |
| `department` | Departmental data silo enforcement |

> *Tóm tắt (VI): Tích hợp SSO qua giao thức OAuth2/OIDC. Hỗ trợ Microsoft Entra ID (Active Directory), Okta và Google Workspace. Người dùng đăng nhập một lần — hệ thống tự động xác thực qua token JWT.*

---

### 4B. Granular Data Isolation — RBAC + Vector Metadata Filtering

**Problem**: In a multi-department company, HR must not retrieve IT financial data, and vice versa. A naive RAG retriever returns chunks from all documents regardless of the requester's authorization.

**Solution**: Tag every document chunk with **permission metadata** at ingestion time, and apply **server-side metadata filters** at retrieval time.

#### Ingestion Pipeline (modified)

```python
# rag_service.py — ingest_document (Phase 4 extension)
doc.metadata["filename"]   = filename
doc.metadata["department"] = department_tag   # e.g. "HR", "IT", "FINANCE"
doc.metadata["acl"]        = ["hr-staff", "hr-manager"]  # allowed role list
doc.metadata["sensitivity"] = "CONFIDENTIAL"  # PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED
```

#### Retrieval Pipeline (modified)

```python
# At query time: inject user's roles from JWT into the filter
user_roles = request.state.user["groups"]   # ["hr-staff", "it-admin"]

retriever = vector_store.as_retriever(
    search_kwargs={
        "k": 2,
        "filter": {
            "acl": {"$in": user_roles}   # Qdrant payload filter
        }
    }
)
```

**Result**: The LLM only ever sees context chunks the requesting user is entitled to access. Data isolation is enforced at the **database query layer** — not just in the UI.

| Role | Accessible documents |
|---|---|
| `hr-staff` | HR policies, employee handbook |
| `it-admin` | IT security policy, network diagrams |
| `finance-manager` | Budget reports, financial statements |
| `executive` | All of the above |

> *Tóm tắt (VI): Mỗi đoạn văn bản (chunk) được gắn metadata phân quyền (department, acl, sensitivity). Khi truy vấn, hệ thống chỉ trả về các đoạn mà người dùng có quyền đọc — dựa trên vai trò JWT. Dữ liệu HR không bao giờ lọt vào context trả lời câu hỏi của bộ phận IT.*

---

### 4C. Advanced Data Protection

#### Encryption at Rest

| Layer | Mechanism |
|---|---|
| Disk / volume | LUKS full-disk encryption (Linux) or cloud provider KMS (AWS KMS, Azure Key Vault) |
| ChromaDB / Qdrant storage | Stored on encrypted volume |
| Environment secrets | HashiCorp Vault or AWS Secrets Manager (replace `.env` files) |
| Backup snapshots | AES-256-GCM encrypted before offsite transfer |

#### Malware & Pipeline Security — Pre-ingestion Scanning

**Problem**: A malicious user could upload a PDF containing embedded shellcode or macro viruses, which could be executed during file parsing.

**Solution**: Scan every uploaded file with **ClamAV** before it enters the chunking pipeline.

```
POST /upload/
    │
    ▼
File saved to temp_uploads/
    │
    ▼  (NEW — Phase 4)
ClamAV scan (pyclamd or subprocess clamscan)
    ├─ CLEAN  → proceed to poison-pattern check → chunk → embed → store
    └─ THREAT → delete file, return 400 + alert security team (PagerDuty / Slack webhook)
    │
    ▼
Existing poison-pattern regex check (already implemented)
    │
    ▼
ChromaDB / Qdrant ingestion
```

```python
# upload.py — Phase 4 ClamAV integration sketch
import pyclamd

def scan_for_malware(file_path: str) -> None:
    cd = pyclamd.ClamdUnixSocket()
    result = cd.scan_file(file_path)
    if result and result[file_path][0] == "FOUND":
        threat = result[file_path][1]
        raise ValueError(f"Malware detected: {threat}. Upload rejected.")
```

> *Tóm tắt (VI): Mã hóa AES-256 toàn bộ dữ liệu tĩnh (disk + DB). Mọi file upload đều qua ClamAV quét virus/malware trước khi vào pipeline chunking. Phát hiện mối đe dọa → xóa file ngay + cảnh báo nhóm bảo mật.*

---

### 4D. Observability & Audit Trails

**Problem**: The current logging is local `stdout`. There is no record of *who asked what* or *which documents were retrieved* — making compliance audits impossible.

**Solution**: Structured audit events → centralized log aggregation → immutable audit trail.

#### Centralized Logging Migration

```
Current:  Python logging → stdout → Docker log driver (local)
Phase 4:  Python logging → JSON formatter → Logstash → Elasticsearch → Kibana (ELK)
       OR Python logging → JSON formatter → Splunk HEC endpoint
```

#### Audit Event Schema

Every RAG request writes a structured audit event:

```json
{
  "event_type": "rag_query",
  "timestamp": "2026-04-07T13:42:49+07:00",
  "user_id": "u-8f2a1c",
  "user_email": "nguyen.van.a@company.com",
  "department": "HR",
  "session_id": "sess-abc123",
  "question_hash": "sha256:e3b0c44...",
  "standalone_question": "What is the remote work VPN policy?",
  "sources_retrieved": [
    {"filename": "it-security-policy-v2.txt", "chunk_id": "c-019", "similarity": 0.91},
    {"filename": "remote-work-guidelines.txt", "chunk_id": "c-042", "similarity": 0.87}
  ],
  "response_latency_ms": 1240,
  "llm_model": "llama-3.3-70b",
  "compliance_flags": []
}
```

**Compliance standards covered**:

| Standard | Requirement met by audit trail |
|---|---|
| **ISO 27001** | A.12.4 — Logging and monitoring of system events |
| **SOC 2 Type II** | CC7.2 — System monitoring and logging |
| **GDPR** | Article 30 — Records of processing activities |
| **HIPAA** (if applicable) | §164.312(b) — Audit controls |

> *Tóm tắt (VI): Mọi truy vấn RAG đều ghi nhật ký kiểm toán có cấu trúc: ai hỏi, hỏi gì, lúc nào, tài liệu nào được truy xuất. Log tập trung qua ELK Stack hoặc Splunk. Đáp ứng ISO 27001, SOC 2, GDPR.*

---

## 📌 Architectural Disclaimer

> **The current Hugging Face Spaces demo is intentionally optimized for AI Logic & RAG Accuracy** — demonstrating Query Reformulation, multi-turn memory, prompt injection shielding, and source citation. It runs as a Single-Container Monolith within free-tier resource constraints (~1 GB RAM, shared CPU).
>
> **Phase 4 security components** (SSO/OIDC, RBAC metadata filtering, AES-256 encryption, ClamAV malware scanning, ELK audit trails) require **private VPS or cloud infrastructure** (AWS/GCP/Azure) with dedicated compute, encrypted volumes, and isolated network policies. Deploying these on a public free-tier demo would exceed memory limits and expose internal identity infrastructure.
>
> **Full enterprise deployment** is available via `docker-compose.yml` (local/VPS) or a Kubernetes Helm chart (cloud-native). Contact the maintainer for a private deployment walkthrough.

---

> *Tuyên bố kiến trúc (VI): Demo trên Hugging Face được tối ưu cho độ chính xác AI và RAG. Các thành phần bảo mật Phase 4 (SSO, RBAC, mã hóa, quét virus, nhật ký kiểm toán) yêu cầu hạ tầng VPS/Cloud riêng tư và vượt quá giới hạn tài nguyên của free-tier công khai. Liên hệ maintainer để được hướng dẫn triển khai enterprise.*

---

*Last updated: 2026-04-07 | Maintainer: [@VThanhNguyen2002](https://github.com/VThanhNguyen2002)*
