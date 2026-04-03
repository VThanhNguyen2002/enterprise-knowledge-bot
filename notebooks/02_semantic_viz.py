"""
Notebook 2: Semantic Search Visualization
==========================================
Extracts chunk vectors from ChromaDB, reduces to 2D using PCA (CPU-safe
alternative to UMAP — no GPU or extra install needed), and renders a
scatter plot showing semantic clusters with query points overlaid.

Requirements: chromadb, scikit-learn, matplotlib, sentence-transformers
Run: python notebooks/02_semantic_viz.py [--chroma-path ./chroma_data]
"""

import os
import sys
import argparse
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ── Parse args ────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Semantic search vector visualization")
parser.add_argument("--chroma-path", default="./chroma_data", help="Path to ChromaDB persist dir")
parser.add_argument("--query", default="What are the password requirements?", help="Query to visualize")
parser.add_argument("--top-k", type=int, default=3, help="Number of nearest neighbours to highlight")
args = parser.parse_args()

print("=" * 65)
print("  NOTEBOOK 2: Semantic Search Visualization (PCA 2D)")
print("=" * 65)

# ── Load ChromaDB ─────────────────────────────────────────────────────────────
try:
    import chromadb
except ImportError:
    print("❌ chromadb not installed. Run: pip install chromadb")
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
except ImportError:
    print("❌ matplotlib not installed. Run: pip install matplotlib")
    sys.exit(1)

try:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import normalize
except ImportError:
    print("❌ scikit-learn not installed. Run: pip install scikit-learn")
    sys.exit(1)

from langchain_huggingface import HuggingFaceEmbeddings

EMBED_MODEL = "all-MiniLM-L6-v2"

if not os.path.exists(args.chroma_path):
    print(f"❌ ChromaDB path not found: {args.chroma_path}")
    print("   Upload a document via the UI first, then re-run this notebook.")
    sys.exit(1)

print(f"\nChromaDB path : {args.chroma_path}")
print(f"Query         : {args.query}")
print(f"Top-k         : {args.top_k}")

# ── Load all vectors from ChromaDB ────────────────────────────────────────────
client = chromadb.PersistentClient(path=args.chroma_path)
collections = client.list_collections()

if not collections:
    print("❌ No collections found in ChromaDB. Upload a document first.")
    sys.exit(1)

collection = collections[0]
print(f"\nCollection    : '{collection.name}'")

data = collection.get(include=["embeddings", "documents", "metadatas"])
embeddings_matrix = np.array(data["embeddings"])
documents = data["documents"]
metadatas = data["metadatas"]

print(f"Chunks found  : {len(documents)}")

if len(documents) < 3:
    print("⚠️  Need at least 3 chunks for meaningful visualization. Upload more text.")
    sys.exit(1)

# ── Embed the query ────────────────────────────────────────────────────────────
print("\n⏳ Embedding query...")
embed_model = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
query_vec = np.array(embed_model.embed_query(args.query)).reshape(1, -1)

# ── PCA reduction ─────────────────────────────────────────────────────────────
all_vecs = np.vstack([embeddings_matrix, query_vec])
all_vecs_norm = normalize(all_vecs)

pca = PCA(n_components=2, random_state=42)
reduced = pca.fit_transform(all_vecs_norm)
explained = pca.explained_variance_ratio_ * 100

chunk_2d = reduced[:-1]
query_2d = reduced[-1]

# ── Compute cosine similarities for top-k ─────────────────────────────────────
sims = embeddings_matrix @ query_vec.T / (
    np.linalg.norm(embeddings_matrix, axis=1, keepdims=True) *
    np.linalg.norm(query_vec)
)
sims = sims.flatten()
top_k_idx = np.argsort(sims)[-args.top_k:][::-1]

# ── Group by filename for colour coding ───────────────────────────────────────
filenames = [m.get("filename", "unknown") for m in metadatas]
unique_files = list(set(filenames))
colour_map = {f: plt.cm.tab10(i / max(len(unique_files), 1)) for i, f in enumerate(unique_files)}
chunk_colours = [colour_map[f] for f in filenames]

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 8))
ax.set_facecolor("#0f1117")
fig.patch.set_facecolor("#0f1117")

# Base chunks
scatter = ax.scatter(
    chunk_2d[:, 0], chunk_2d[:, 1],
    c=chunk_colours, s=80, alpha=0.7, zorder=2,
    label="Chunks"
)

# Top-k highlighted
ax.scatter(
    chunk_2d[top_k_idx, 0], chunk_2d[top_k_idx, 1],
    s=200, facecolors="none", edgecolors="#00ff88", linewidths=2.5,
    zorder=3, label=f"Top-{args.top_k} retrieved"
)

# Query point
ax.scatter(
    query_2d[0], query_2d[1],
    s=300, marker="*", c="#ff4b4b", zorder=4, label="Query"
)
ax.annotate(
    f"  Query:\n  \"{args.query[:40]}...\"" if len(args.query) > 40 else f"  Query:\n  \"{args.query}\"",
    (query_2d[0], query_2d[1]),
    fontsize=8, color="#ff4b4b", zorder=5
)

# Connector lines from query to top-k
for idx in top_k_idx:
    ax.plot(
        [query_2d[0], chunk_2d[idx, 0]],
        [query_2d[1], chunk_2d[idx, 1]],
        color="#00ff88", alpha=0.4, linewidth=1, linestyle="--", zorder=1
    )

# Filename legend
file_patches = [mpatches.Patch(color=colour_map[f], label=f) for f in unique_files]
legend1 = ax.legend(handles=file_patches, loc="lower left", fontsize=8,
                     facecolor="#1e1e2e", edgecolor="gray", labelcolor="white")
ax.add_artist(legend1)
ax.legend(loc="upper right", fontsize=9, facecolor="#1e1e2e",
          edgecolor="gray", labelcolor="white")

ax.set_title(
    f"Semantic Search Space — PCA 2D Projection\n"
    f"(PC1: {explained[0]:.1f}%  PC2: {explained[1]:.1f}% variance explained | {len(documents)} chunks)",
    color="white", fontsize=12, pad=12
)
ax.tick_params(colors="gray")
for spine in ax.spines.values():
    spine.set_edgecolor("#333")

plt.tight_layout()
out_path = os.path.join(os.path.dirname(__file__), "02_semantic_viz_output.png")
plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"\n✅ Plot saved to: {out_path}")
plt.show()

print("\nTop retrieved chunks:")
for rank, idx in enumerate(top_k_idx, 1):
    snippet = documents[idx][:100].replace("\n", " ")
    fname = filenames[idx]
    print(f"  #{rank} (sim={sims[idx]:.3f}) [{fname}]: {snippet}...")
