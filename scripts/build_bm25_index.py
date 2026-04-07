#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from src.retrieval.bm25_engine import BM25Engine


def load_chunks_from_jsonl(path: Path):
    chunks = []
    if not path.exists():
        raise FileNotFoundError(f"Chunks file not found: {path}")

    # Support both JSON (list) and JSONL (one JSON per line)
    with open(path, "r", encoding="utf-8") as f:
        first = f.readline()
        if not first:
            return []
        first_stripped = first.lstrip()
        f.seek(0)
        if first_stripped.startswith("["):
            # JSON array
            data = json.load(f)
            for item in data:
                chunks.append({
                    "id": item.get("id") or item.get("uid"),
                    "text": item.get("text") or item.get("claim") or "",
                    "metadata": item.get("metadata", {})
                })
        else:
            # JSONL
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                chunks.append({
                    "id": item.get("id") or item.get("uid"),
                    "text": item.get("text") or item.get("claim") or "",
                    "metadata": item.get("metadata", {})
                })
    return chunks


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--chunks", type=Path, help="Path to chunks json or jsonl", 
                   default=Path("data/interim/sentence_chunks/sentence_chunks.jsonl"))
    p.add_argument("--out", type=Path, help="Output path for saved BM25 index pickle",
                   default=Path("data/processed/bm25_paragraph_index.pkl"))
    p.add_argument("--k1", type=float, default=1.5)
    p.add_argument("--b", type=float, default=0.75)
    args = p.parse_args()

    print(f"Loading chunks from {args.chunks}")
    chunks = load_chunks_from_jsonl(args.chunks)
    print(f"Loaded {len(chunks)} chunks")

    config = SimpleNamespace()
    config.bm25_k1 = args.k1
    config.bm25_b = args.b
    config.data_dir = Path("data")
    config.bm25_index_path = args.out

    engine = BM25Engine(config)
    engine.build_index(chunks)

    print("Done. Index saved to:", args.out)


if __name__ == "__main__":
    main()
