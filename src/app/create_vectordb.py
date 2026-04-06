from src.common.config import Config

from src.data.utils import ensure_dir
from src.data.data_loader import load_hover_dataset_from_local_json
from src.data.hover_sampler import run_hover_sampling
from src.data.wiki_matcher import run_wiki_matching
from src.data.chunker import run_chunking
from src.data.gold_mapper import run_gold_mapping

from src.retrieval.chroma_builder import upsert_chunks
from src.retrieval.retriever import batch_retrieve

def prepare_dirs(config: Config) -> None:
    ensure_dir(config.raw_dir)
    ensure_dir(config.wiki_cache_dir)
    ensure_dir(config.interim_dir / "sampled_hover")
    ensure_dir(config.interim_dir / "matched_wiki_docs")
    ensure_dir(config.interim_dir / "sentence_chunks")
    ensure_dir(config.processed_dir / "hover_with_gold_chunks")
    ensure_dir(config.processed_dir / "eval_results")
    ensure_dir(config.chroma_dir)


def main():
    config = Config()
    prepare_dirs(config)

    print("[1/6] Loading HoVer local json...")
    hover_rows = load_hover_dataset_from_local_json(config.hover_train_json_path)
    print(f"  - hover rows: {len(hover_rows)}")

    print("[2/6] Sampling HoVer claims...")
    sampled_claims, required_titles = run_hover_sampling(hover_rows, config)
    print(f"  - sampled claims: {len(sampled_claims)}")
    print(f"  - required wiki titles: {len(required_titles)}")

    print("[3/6] Loading/FETCHING Wikipedia documents with local cache...")
    matched_docs, missing_titles = run_wiki_matching(required_titles, config)
    print(f"  - matched docs: {len(matched_docs)}")
    print(f"  - missing titles: {len(missing_titles)}")
    if missing_titles:
        print("  - missing title examples:", missing_titles[:5])

    print("[4/6] Building sentence chunks...")
    chunks = run_chunking(matched_docs, config)
    print(f"  - total sentence chunks: {len(chunks)}")

    print("[5/6] Building gold mappings...")
    enriched_claims = run_gold_mapping(sampled_claims, config)

    print("[6/6] Upserting into Chroma...")
    upsert_chunks(chunks, config)

    for top_k in config.top_k_list:
        retrieval_rows = batch_retrieve(enriched_claims, top_k=top_k, config=config)
        print(retrieval_rows)
    print("Done.")


if __name__ == "__main__":
    main()