from pathlib import Path
from types import SimpleNamespace
import time

from src.retrieval.bm25_engine import BM25Engine

# Minimal dummy config to avoid importing Config (which requires HF_TOKEN)
config = SimpleNamespace()
config.bm25_k1 = 1.5
config.bm25_b = 0.75
config.data_dir = Path(__file__).resolve().parent.parent / "data"
config.bm25_index_path = config.data_dir / "processed" / "bm25_test_index.pkl"

# Sample chunks
chunks = [
    {"id": "c1", "text": "The quick brown fox jumps over the lazy dog.", "metadata": {"source": "doc1"}},
    {"id": "c2", "text": "Python is a programming language that emphasizes readability.", "metadata": {"source": "doc2"}},
    {"id": "c3", "text": "Artificial intelligence and machine learning are related fields.", "metadata": {"source": "doc3"}},
    {"id": "c4", "text": "The capital of France is Paris, known for the Eiffel Tower.", "metadata": {"source": "doc4"}},
    {"id": "c5", "text": "Baseball is a popular sport in the United States.", "metadata": {"source": "doc5"}},
]

print("[TEST] Creating BM25 engine and building index...")
engine = BM25Engine(config)
start = time.time()
engine.build_index(chunks)
build_time = time.time() - start
print(f"[TEST] Build time: {build_time:.4f}s")

query = "Which city is known for the Eiffel Tower?"
start = time.time()
res = engine.query(query, n_results=3)
qtime = time.time() - start
print(f"[TEST] Query time: {qtime:.6f}s")
print("[TEST] Results:")
print(res)

print("[TEST] Done.")
