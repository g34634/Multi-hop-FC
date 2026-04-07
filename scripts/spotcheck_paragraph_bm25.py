#!/usr/bin/env python3
"""
Create paragraph samples from gold chunk ids, build BM25 index and spot-check whether
gold chunk ids appear in top-k retrieval results for their claims.

Usage:
  PYTHONPATH=. python3 scripts/spotcheck_paragraph_bm25.py --n_samples 5 --top_k 5

"""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from src.retrieval.bm25_engine import BM25Engine


def load_sentence_dict(sent_jsonl_path: Path):
    d = {}
    if not sent_jsonl_path.exists():
        raise FileNotFoundError(sent_jsonl_path)
    with open(sent_jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            sid = obj.get("id")
            if sid:
                d[sid] = obj.get("text", "")
    return d


def load_hover(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_paragraph_chunks(hover_items, sentence_dict, sentences_forward=1, sample_n=5):
    """
    For each hover item, for each gold_chunk_id, create a paragraph by taking the
    sentence at that id plus the next `sentences_forward` sentences (if present).
    The produced chunk id will be the same gold_chunk_id (so matching is direct).
    """
    chunks = []
    count = 0
    for item in hover_items:
        if count >= sample_n:
            break
        claim = item.get("claim")
        gold_ids = item.get("gold_chunk_ids", [])
        if not gold_ids:
            continue
        # For spotcheck we will include all gold ids for this claim as separate chunks
        for gid in gold_ids:
            # gid example: wiki::Title::2
            text = sentence_dict.get(gid, "")
            if text == "":
                # try to fallback: if gid ends with ::N, try consecutive ids
                text = sentence_dict.get(gid, "")
            # Try to append next sentence if exists
            try:
                parts = gid.rsplit("::", 1)
                base = parts[0]
                idx = int(parts[1])
                texts = [sentence_dict.get(f"{base}::{idx}", "")]
                for j in range(1, sentences_forward+1):
                    candidate = sentence_dict.get(f"{base}::{idx + j}", "")
                    if candidate:
                        texts.append(candidate)
                para_text = " ".join([t for t in texts if t])
            except Exception:
                para_text = text

            if not para_text:
                continue
            chunks.append({
                "id": gid,
                "text": para_text,
                "metadata": {"source_claim": claim}
            })
        count += 1
    return chunks


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n_samples", type=int, default=5)
    p.add_argument("--top_k", type=int, default=5)
    p.add_argument("--sentences_forward", type=int, default=1,
                   help="how many sentences after the gold sentence to append to paragraph")
    args = p.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    sentence_jsonl = repo_root / "data" / "interim" / "sentence_chunks" / "sentence_chunks.jsonl"
    hover_json = repo_root / "data" / "processed" / "hover_with_gold_chunks" / "hover_with_gold.json"

    sentence_dict = load_sentence_dict(sentence_jsonl)
    hover_items = load_hover(hover_json)

    print(f"Loaded {len(sentence_dict)} sentences and {len(hover_items)} hover items")

    chunks = build_paragraph_chunks(hover_items, sentence_dict, sentences_forward=args.sentences_forward, sample_n=args.n_samples)
    print(f"Built {len(chunks)} paragraph chunks (sample_n={args.n_samples})")

    # build bm25
    config = SimpleNamespace()
    config.bm25_k1 = 1.5
    config.bm25_b = 0.75
    config.data_dir = repo_root / "data"
    config.bm25_index_path = repo_root / "data" / "processed" / "bm25_spotcheck_index.pkl"

    engine = BM25Engine(config)
    engine.build_index(chunks)

    # For each hover item in sample, run query and see if any of its gold ids are retrieved
    results = []
    sample_hover = hover_items[: args.n_samples]
    for item in sample_hover:
        claim = item.get("claim", "")
        gold_ids = set(item.get("gold_chunk_ids", []))
        raw = engine.query(claim, n_results=args.top_k)
        retrieved = raw.get("ids", [[]])[0]
        hit = any(r in gold_ids for r in retrieved)
        results.append({
            "uid": item.get("uid"),
            "claim": claim,
            "gold_ids": list(gold_ids),
            "retrieved": retrieved,
            "hit": hit,
        })

    # print summary
    hits = sum(1 for r in results if r["hit"]) if results else 0
    print(f"Spotcheck: {hits}/{len(results)} claims had at least one gold id in top-{args.top_k}")
    for r in results:
        print("---")
        print("UID:", r["uid"]) 
        print("Claim:", r["claim"]) 
        print("Gold IDs:", r["gold_ids"]) 
        print("Retrieved:", r["retrieved"]) 
        print("Hit:", r["hit"]) 


if __name__ == "__main__":
    main()
