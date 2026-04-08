from pathlib import Path
from types import SimpleNamespace
import json
import shutil

import pandas as pd

from src.retrieval.bm25_engine import BM25Engine


def load_parquet_as_chunks(parquet_path: Path) -> list[dict]:
    parquet_path = Path(parquet_path)
    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet not found: {parquet_path}")

    df = pd.read_parquet(parquet_path)

    chunks: list[dict] = []
    for row in df.itertuples(index=False):
        chunks.append(
            {
                "id": row.paragraph_uid,
                "text": row.paragraph_text,
                "metadata": {
                    "doc_id": row.doc_id,
                    "title": row.title,
                    "title_norm": row.title_norm,
                    "paragraph_id": row.paragraph_id,
                    "paragraph_index": row.paragraph_index,
                    "source_path": row.source_path,
                    "record_id": row.record_id,
                },
            }
        )

    return chunks


def list_parquet_files(parquet_dir: Path) -> list[Path]:
    parquet_dir = Path(parquet_dir)
    if not parquet_dir.exists():
        raise FileNotFoundError(f"Parquet directory not found: {parquet_dir}")

    parquet_files = sorted(parquet_dir.rglob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found under: {parquet_dir}")

    return parquet_files


def load_parquet_dir_as_chunks(parquet_dir: Path) -> list[dict]:
    parquet_files = list_parquet_files(parquet_dir)

    all_chunks: list[dict] = []
    for idx, parquet_path in enumerate(parquet_files, start=1):
        print(f"[{idx}/{len(parquet_files)}] Loading parquet: {parquet_path}")
        chunks = load_parquet_as_chunks(parquet_path)
        all_chunks.extend(chunks)

    return all_chunks


def iter_parquet_dir_chunk_batches(
    parquet_dir: Path,
    files_per_batch: int = 100,
):
    """
    Yield chunk lists in file-batches to reduce peak memory during loading.
    """
    if files_per_batch <= 0:
        raise ValueError("files_per_batch must be > 0")

    parquet_files = list_parquet_files(parquet_dir)
    total_files = len(parquet_files)

    for start in range(0, total_files, files_per_batch):
        end = min(start + files_per_batch, total_files)
        batch_files = parquet_files[start:end]
        batch_chunks: list[dict] = []

        for idx, parquet_path in enumerate(batch_files, start=start + 1):
            print(f"[{idx}/{total_files}] Loading parquet: {parquet_path}")
            chunks = load_parquet_as_chunks(parquet_path)
            batch_chunks.extend(chunks)

        yield batch_chunks, start, end, total_files


def _write_chunks_to_jsonl_file(chunks: list[dict], jsonl_path: Path) -> None:
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            obj = {
                "id": str(chunk.get("id", "")),
                "contents": chunk.get("text", "") or "",
                "metadata": chunk.get("metadata", {}) or {},
            }
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def build_bm25_index_from_parquet(
    parquet_path: Path,
    output_path: Path,
    k1: float = 1.5,
    b: float = 0.75,
):
    print(f"Loading parquet: {parquet_path}")
    chunks = load_parquet_as_chunks(parquet_path)
    print(f"Loaded {len(chunks)} chunks")

    config = SimpleNamespace()
    config.bm25_k1 = k1
    config.bm25_b = b
    config.data_dir = Path("data")
    config.bm25_index_path = Path(output_path)

    engine = BM25Engine(config)
    engine.build_index(chunks)

    print("BM25 index built:", engine.config.bm25_index_path)


def build_bm25_index_from_parquet_dir_batched(
    parquet_dir: Path,
    output_path: Path,
    k1: float = 1.5,
    b: float = 0.75,
    files_per_batch: int = 100,
):
    """
    Convert parquet shards to batched JSONL files and build one Lucene BM25
    index from that directory. This avoids loading all chunks into memory.
    """
    print(f"Loading parquet directory in batches: {parquet_dir}")
    print(f"files_per_batch: {files_per_batch}")

    output_path = Path(output_path)
    temp_jsonl_dir = output_path.parent / f"{output_path.name}_jsonl_tmp"
    if temp_jsonl_dir.exists():
        shutil.rmtree(temp_jsonl_dir)
    temp_jsonl_dir.mkdir(parents=True, exist_ok=True)

    total_chunks = 0
    batch_no = 0
    for batch_chunks, start, end, total_files in iter_parquet_dir_chunk_batches(
        parquet_dir=parquet_dir,
        files_per_batch=files_per_batch,
    ):
        batch_no += 1
        total_chunks += len(batch_chunks)
        batch_jsonl = temp_jsonl_dir / f"part_{batch_no:05d}.jsonl"
        _write_chunks_to_jsonl_file(batch_chunks, batch_jsonl)
        print(
            f"Loaded files {start + 1}-{end}/{total_files} | "
            f"batch_chunks={len(batch_chunks)} | "
            f"total_chunks={total_chunks} | "
            f"written={batch_jsonl.name}"
        )

    config = SimpleNamespace()
    config.bm25_k1 = k1
    config.bm25_b = b
    config.bm25_threads = 4
    config.data_dir = Path("data")
    config.bm25_index_path = output_path

    engine = BM25Engine(config)
    engine.build_index_from_jsonl_dir(temp_jsonl_dir, overwrite=True)

    shutil.rmtree(temp_jsonl_dir, ignore_errors=True)
    print("BM25 index built:", engine.config.bm25_index_path)


def build_bm25_index_from_parquet_dir(
    parquet_dir: Path,
    output_path: Path,
    k1: float = 1.5,
    b: float = 0.75,
):
    # Route to batched builder by default for safer memory behavior.
    build_bm25_index_from_parquet_dir_batched(
        parquet_dir=parquet_dir,
        output_path=output_path,
        k1=k1,
        b=b,
        files_per_batch=100,
    )


def build_bm25_index_from_jsonl_tmp_dir(
    jsonl_tmp_dir: Path,
    output_path: Path,
    k1: float = 1.5,
    b: float = 0.75,
    threads: int = 4,
):
    """
    Build Lucene BM25 index directly from an existing JSONL shard directory.
    Example input dir:
      data/interim/bm25/bm25_index_all_shards_lucene_jsonl_tmp
      (contains part_00001.jsonl, ..., part_00122.jsonl)
    """
    jsonl_tmp_dir = Path(jsonl_tmp_dir)
    output_path = Path(output_path)

    if not jsonl_tmp_dir.exists():
        raise FileNotFoundError(f"JSONL temp directory not found: {jsonl_tmp_dir}")

    jsonl_files = sorted(jsonl_tmp_dir.glob("*.jsonl"))
    if not jsonl_files:
        raise FileNotFoundError(f"No .jsonl files found under: {jsonl_tmp_dir}")

    print(f"JSONL files found: {len(jsonl_files)}")
    print(f"first: {jsonl_files[0].name}")
    print(f"last : {jsonl_files[-1].name}")

    config = SimpleNamespace()
    config.bm25_k1 = k1
    config.bm25_b = b
    config.bm25_threads = threads
    config.data_dir = Path("data")
    config.bm25_index_path = output_path

    engine = BM25Engine(config)
    engine.build_index_from_jsonl_dir(input_dir=jsonl_tmp_dir, overwrite=True)
    print("BM25 index built:", engine.config.bm25_index_path)
