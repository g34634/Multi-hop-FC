from __future__ import annotations

import argparse
from pathlib import Path

from src.common.config import Config
from src.retrieval.retriever import BM25Retriever


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BM25Retriever example runner")
    parser.add_argument(
        "--query",
        type=str,
        default="The Godfather was directed by Christopher Nolan.",
        help="Query text for BM25 retrieval",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of documents to retrieve",
    )
    parser.add_argument(
        "--index-path",
        type=Path,
        default=None,
        help="Optional BM25 index path override",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    cfg = Config()

    if args.index_path is not None:
        cfg.bm25_index_path = args.index_path

    retriever = BM25Retriever(config=cfg, top_k=args.top_k)
    results = retriever.retrieve_for_claim(args.query)

    print(f"[BM25 index path] {cfg.bm25_index_path}")
    print(f"[Query] {args.query}")
    print(f"[Retrieved] {len(results)} docs")

    for i, doc in enumerate(results, start=1):
        print(f"\n--- Doc {i} ---")
        print("id:", doc.get("id"))
        print("score:", doc.get("score"))
        print("metadata:", doc.get("metadata", {}))
        print("text:", doc.get("text", ""))


if __name__ == "__main__":
    main()
