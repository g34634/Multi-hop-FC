from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    # -------------------------
    # Paths
    # -------------------------
    project_root: Path = Path(__file__).resolve().parent.parent.parent
    data_dir: Path = project_root / "data"
    raw_dir: Path = data_dir / "raw"
    interim_dir: Path = data_dir / "interim"
    processed_dir: Path = data_dir / "processed"
    chroma_dir: Path = project_root / "chroma_db"

    # HoVer local json
    hover_train_json_path: Path = raw_dir / "hover" / "hover_train_release_v1.1.json"

    # Wikipedia cache directory
    wiki_cache_dir: Path = raw_dir / "wiki_cache"

    sampled_hover_path: Path = interim_dir / "sampled_hover" / "sampled_claims.json"
    required_titles_path: Path = interim_dir / "sampled_hover" / "required_titles.json"
    matched_wiki_docs_path: Path = interim_dir / "matched_wiki_docs" / "matched_docs.json"
    sentence_chunks_path: Path = interim_dir / "sentence_chunks" / "sentence_chunks.jsonl"

    hover_with_gold_path: Path = processed_dir / "hover_with_gold_chunks" / "hover_with_gold.json"
    eval_results_path: Path = processed_dir / "eval_results" / "retrieval_eval.json"

    # -------------------------
    # HF_TOKEN
    # -------------------------
    HF_TOKEN = os.getenv("HF_TOKEN", None)
    if not HF_TOKEN:
        raise ValueError("Please set HF_TOKEN environment variable.")

    # -------------------------
    # Sampling
    # -------------------------
    target_num_hops: int = 2
    sample_size: int = 10
    random_seed: int = 42

    # -------------------------
    # Chunking
    # -------------------------
    min_sentence_char_len: int = 5
    lowercase_titles_for_id: bool = False

    # -------------------------
    # Wikipedia API
    # -------------------------
    wiki_api_url: str = "https://en.wikipedia.org/w/api.php"
    wiki_request_timeout: int = 30
    wiki_sleep_sec: float = 0.2
    wiki_force_refresh: bool = False

    # -------------------------
    # Embedding / Chroma
    # -------------------------
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    collection_name: str = "hover_wiki_sentence"
    distance_metric: str = "cosine"
    batch_size: int = 128
    chroma_recreate_collection: bool = False

    # -------------------------
    # Retrieval
    # -------------------------
    top_k_list: list[int] = field(default_factory=lambda: [1, 3, 5, 10])
    bm25_index_path: Path = interim_dir / "bm25_index"
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    bm25_threads: int = max(1, (os.cpu_count() or 1) // 2)

@dataclass
class ProgramFCConfig(Config):
    # Planner
    planner_model: str = "gpt-5.3-codex"
    openai_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )
    planner_temperature: float = 0.7
    planner_max_output_tokens: int = 800

    # Executor
    executor_model: str = "Qwen/Qwen3-8B"
    executor_max_new_tokens: int = 128

    # Retrieval
    closed_book: bool = False

    # Pipeline
    num_programs: int = 5
    error_log_path: str = "outputs/logs/programfc_errors.jsonl"
