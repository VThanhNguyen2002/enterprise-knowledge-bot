"""
Notebook 1: Chunking Strategy Evaluation
=========================================
Evaluates how chunk_size (200 vs 500 vs 1000) affects retrieval quality
on a sample document. Runs entirely offline — no LLM API calls needed.

Requirements: sentence-transformers, langchain-text-splitters,
              langchain-community, chromadb, tabulate
Run: python notebooks/01_chunking_eval.py
"""

import os
import sys
import time
import tempfile
import textwrap
from tabulate import tabulate

# ── Ensure project root is on path ────────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import TextLoader

# ── Sample knowledge document ──────────────────────────────────────────────────
SAMPLE_TEXT = """
Enterprise IT Security Policy v2.1

1. Password Management
All employees must use passwords of at least 12 characters, combining uppercase,
lowercase, numbers, and special symbols. Passwords must be changed every 90 days.
Sharing passwords is strictly prohibited and may result in disciplinary action.

2. Remote Access
VPN usage is mandatory when accessing company resources from outside the office.
Two-factor authentication (2FA) must be enabled on all accounts. Unapproved
remote desktop tools such as TeamViewer are not permitted.

3. Data Classification
Company data is classified into four levels: Public, Internal, Confidential,
and Restricted. Restricted data (financial records, PII) must be encrypted at
rest and in transit. Storage on personal devices is prohibited.

4. Incident Response
Security incidents must be reported to the IT Security team within 2 hours of
discovery. The incident response team will conduct a root cause analysis within
72 hours. All breaches involving customer data trigger mandatory regulatory
notification within 72 hours.

5. Software and Device Policy
Only approved software from the company app catalog may be installed on
corporate devices. All devices must run the latest OS patches within 30 days
of release. Unmanaged personal devices may not connect to the corporate network.

6. Acceptable Use
Company resources are for business purposes only. Monitoring of network traffic
is conducted continuously. Employees found misusing resources will face
disciplinary procedures up to and including termination.
""".strip()

# ── Test queries ───────────────────────────────────────────────────────────────
TEST_QUERIES = [
    "What is the password expiration policy?",
    "Is VPN required for remote work?",
    "How are security incidents reported?",
    "What software can be installed on company devices?",
    "How is restricted data handled?",
]

CHUNK_SIZES = [200, 500, 1000]
EMBED_MODEL = "all-MiniLM-L6-v2"

print("=" * 70)
print("  NOTEBOOK 1: Chunking Strategy Evaluation")
print("=" * 70)
print(f"\nEmbedding model : {EMBED_MODEL}")
print(f"Chunk sizes     : {CHUNK_SIZES}")
print(f"Test queries    : {len(TEST_QUERIES)}")
print(f"Retriever k     : 2\n")

print("⏳ Loading embedding model (this may take ~30s on first run)...")
embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
print("✅ Model loaded.\n")

results_table = []

# ── Create temp file with sample text ─────────────────────────────────────────
with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
    f.write(SAMPLE_TEXT)
    tmp_path = f.name

loader = TextLoader(tmp_path, encoding="utf-8")
docs = loader.load()

for chunk_size in CHUNK_SIZES:
    print(f"{'─' * 50}")
    print(f"  chunk_size = {chunk_size:>4d}  |  overlap = {chunk_size // 10}")
    print(f"{'─' * 50}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_size // 10,
    )
    chunks = splitter.split_documents(docs)
    print(f"  Chunks created : {len(chunks)}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        t0 = time.time()
        vs = Chroma.from_documents(chunks, embeddings, persist_directory=tmp_dir)
        embed_time = time.time() - t0
        print(f"  Embed + store  : {embed_time:.2f}s")

        retriever = vs.as_retriever(search_kwargs={"k": 2})
        hit_counts = []

        for query in TEST_QUERIES:
            found_docs = retriever.invoke(query)
            first_snippet = found_docs[0].page_content[:80].replace("\n", " ") if found_docs else "—"
            has_relevant = any(
                any(kw in d.page_content.lower() for kw in query.lower().split()[:3])
                for d in found_docs
            )
            hit_counts.append(1 if has_relevant else 0)
            print(f"  Q: {query[:50]:<50} | {'✅ HIT' if has_relevant else '❌ MISS'}")

        hit_rate = sum(hit_counts) / len(hit_counts) * 100
        results_table.append({
            "chunk_size": chunk_size,
            "n_chunks": len(chunks),
            "embed_time_s": round(embed_time, 2),
            "hit_rate_%": round(hit_rate, 1),
        })
        print()

os.unlink(tmp_path)  # cleanup temp file

# ── Summary Table ──────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  RESULTS SUMMARY")
print("=" * 70)
print(tabulate(
    [[r["chunk_size"], r["n_chunks"], r["embed_time_s"], f"{r['hit_rate_%']}%"]
     for r in results_table],
    headers=["Chunk Size", "# Chunks", "Embed Time (s)", "Retrieval Hit Rate"],
    tablefmt="rounded_outline",
))

best = max(results_table, key=lambda x: x["hit_rate_%"])
print(f"\n✅ Recommended chunk_size: {best['chunk_size']} (hit rate: {best['hit_rate_%']}%)")
print("\nConclusion: Smaller chunks improve precision but create more vectors.")
print("Larger chunks preserve context but may dilute relevance scores.")
