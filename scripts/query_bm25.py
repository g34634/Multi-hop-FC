#!/usr/bin/env python3
"""
Load BM25 index (or build from default chunks) and run queries provided on CLI.

Usage examples:
  PYTHONPATH=. python3 scripts/query_bm25.py --index data/processed/bm25_full_index.pkl --top_k 5 --query "..." --query "..."

If no index exists, the script will build from `data/interim/sentence_chunks/sentence_chunks.jsonl`.
"""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from src.retrieval.bm25_engine import BM25Engine


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--index", type=Path, default=Path("data/processed/bm25_full_index.pkl"))
    p.add_argument("--top_k", type=int, default=5)
    p.add_argument("--query", action="append", help="Query text. Can be repeated.")
    args = p.parse_args()

    repo_root = Path(__file__).resolve().parent.parent

    # prepare config
    config = SimpleNamespace()
    config.bm25_k1 = 1.5
    config.bm25_b = 0.75
    config.data_dir = repo_root / "data"
    config.bm25_index_path = args.index

    engine = BM25Engine(config)

    # If index not loaded and not exists, build from default chunks file
    if engine.bm25 is None:
        # try to build from sentence chunks
        chunks_path = repo_root / "data" / "interim" / "sentence_chunks" / "sentence_chunks.jsonl"
        if not chunks_path.exists():
            print("No existing index and no chunks file found at:", chunks_path)
            return
        print("No index loaded, building from:", chunks_path)
        # load chunks (simple loader)
        chunks = []
        with open(chunks_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                chunks.append({
                    "id": obj.get("id"),
                    "text": obj.get("text", ""),
                    "metadata": obj.get("metadata", {}),
                })
        print(f"Building index for {len(chunks)} chunks...")
        engine.build_index(chunks)

    queries = args.query or [
        "Skagen Painter Peder Severin Krøyer favored naturalism along with Theodor Esbern Philipsen and Kristian Zahrtmann.",
        "Red, White & Crüe and Mike Tyson both died.",
    ]

    for q in queries:
        print("\n=== Query: ")
        print(q)
        res = engine.query(q, n_results=args.top_k)
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        scores = res.get("distances", [[]])[0]
        for i in range(len(ids)):
            print(f"#{i+1} id={ids[i]} score={scores[i]:.4f}")
            print(docs[i][:300].replace('\n',' '))
            print("meta=", metas[i])

if __name__ == "__main__":
    main()
