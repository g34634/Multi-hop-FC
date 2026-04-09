from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import sys
from collections import defaultdict
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

import pandas as pd
from tqdm.auto import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.data.gold_mapper import build_title_to_sentence_store, enrich_hover_claim_row
from src.data.hover_loader import load_hover_json


PARQUET_COLUMNS = [
    "paragraph_uid",
    "paragraph_text",
    "title",
    "title_norm",
    "paragraph_id",
    "paragraph_index",
    "doc_id",
    "source_path",
    "record_id",
]


# 대상 title 집합을 짧은 해시 키로 바꿔 캐시/체크포인트 파일명에 사용한다.
def _title_filter_key(target_titles: set[str] | None) -> str:
    if not target_titles:
        return "all"
    digest = hashlib.sha1("\n".join(sorted(target_titles)).encode("utf-8")).hexdigest()
    return digest[:12]


# parquet 파일명과 title 필터 키를 조합해 체크포인트 경로를 만든다.
def _checkpoint_path(checkpoint_dir: Path, parquet_file: str, title_filter_key: str = "all") -> Path:
    p = Path(parquet_file)
    return checkpoint_dir / f"{p.parent.name}_{p.stem}_{title_filter_key}.pkl"


# 샤드별 청크 체크포인트를 로드하고, 손상 시 삭제 후 None을 반환한다.
def _load_checkpoint(checkpoint_path: Path) -> list[dict] | None:
    if not checkpoint_path.exists():
        return None

    try:
        with checkpoint_path.open("rb") as f:
            return pickle.load(f)
    except Exception:
        checkpoint_path.unlink(missing_ok=True)
        return None


# 샤드별 청크 변환 결과를 원자적으로 저장해 재시작 시 재사용한다.
def _save_checkpoint(checkpoint_path: Path, chunks: list[dict]) -> None:
    tmp_path = checkpoint_path.with_suffix(".tmp")
    with tmp_path.open("wb") as f:
        pickle.dump(chunks, f, protocol=pickle.HIGHEST_PROTOCOL)
    tmp_path.replace(checkpoint_path)


# parquet 샤드를 retrieval chunk 포맷으로 변환하고 체크포인트 캐시를 적용한다.
def _parquet_to_chunks(
    parquet_file: str,
    checkpoint_dir: Path,
    target_titles: set[str] | None = None,
) -> list[dict]:
    title_filter_key = _title_filter_key(target_titles)
    checkpoint_path = _checkpoint_path(checkpoint_dir, parquet_file, title_filter_key)
    cached = _load_checkpoint(checkpoint_path)
    if cached is not None:
        return cached

    df = pd.read_parquet(parquet_file, columns=PARQUET_COLUMNS)
    if target_titles:
        df = df[df["title"].isin(target_titles)]
    rows = df[PARQUET_COLUMNS].itertuples(index=False, name=None)

    chunks = [
        {
            "id": paragraph_uid,
            "text": paragraph_text,
            "metadata": {
                "title": title,
                "title_norm": title_norm,
                "paragraph_id": paragraph_id,
                "paragraph_index": paragraph_index,
                "doc_id": doc_id,
                "source_path": source_path,
                "record_id": record_id,
            },
        }
        for (
            paragraph_uid,
            paragraph_text,
            title,
            title_norm,
            paragraph_id,
            paragraph_index,
            doc_id,
            source_path,
            record_id,
        ) in rows
    ]

    _save_checkpoint(checkpoint_path, chunks)
    return chunks


# parquet 샤드 집합의 시그니처(개수/크기/mtime/이름)를 계산한다.
def _parquet_signature(parquet_files: list[Path], parquet_shards_dir: Path) -> dict:
    total_size = 0
    max_mtime_ns = 0
    rel_names: list[str] = []
    for p in parquet_files:
        st = p.stat()
        total_size += int(st.st_size)
        max_mtime_ns = max(max_mtime_ns, int(st.st_mtime_ns))
        rel_names.append(str(p.relative_to(parquet_shards_dir)))
    return {
        "count": len(parquet_files),
        "total_size": total_size,
        "max_mtime_ns": max_mtime_ns,
        "rel_names": rel_names,
    }


# title_to_chunks 캐시를 시그니처와 함께 검증해 유효할 때만 로드한다.
def _load_title_chunks_cache(cache_path: Path, expected_signature: dict) -> dict[str, list[dict]] | None:
    if not cache_path.exists():
        return None
    try:
        with cache_path.open("rb") as f:
            payload = pickle.load(f)
        if (
            isinstance(payload, dict)
            and payload.get("signature") == expected_signature
            and isinstance(payload.get("title_to_chunks"), dict)
        ):
            return payload["title_to_chunks"]
    except Exception:
        pass
    return None


# title_to_chunks 인덱스를 시그니처와 함께 원자적으로 저장한다.
def _save_title_chunks_cache(cache_path: Path, signature: dict, title_to_chunks: dict[str, list[dict]]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.with_suffix(".tmp")
    payload = {
        "signature": signature,
        "title_to_chunks": title_to_chunks,
    }
    with tmp_path.open("wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    tmp_path.replace(cache_path)


# in-flight 개수를 제한하며 샤드 변환 future를 순차적으로 yield한다.
def _iter_shard_results_bounded(
    parquet_files: list[Path],
    checkpoint_dir: Path,
    executor: ThreadPoolExecutor,
    max_in_flight: int,
    target_titles: set[str] | None = None,
):
    files_iter = iter(parquet_files)
    future_to_file: dict = {}

    for _ in range(max_in_flight):
        try:
            p = next(files_iter)
        except StopIteration:
            break
        future = executor.submit(_parquet_to_chunks, str(p), checkpoint_dir, target_titles)
        future_to_file[future] = p

    while future_to_file:
        done, _pending = wait(future_to_file.keys(), return_when=FIRST_COMPLETED)
        for future in done:
            shard_path = future_to_file.pop(future)
            yield shard_path, future

            try:
                next_path = next(files_iter)
            except StopIteration:
                continue
            next_future = executor.submit(_parquet_to_chunks, str(next_path), checkpoint_dir, target_titles)
            future_to_file[next_future] = next_path


# CLI 인자를 파싱하고 데이터 경로/스레드 설정 기본값을 구성한다.
def parse_args() -> argparse.Namespace:
    default_parquet_shards_dir = (
        PROJECT_ROOT / "data" / "interim" / "normalized_paragraphs" / "notebook_all_shards" / "shards"
    )
    default_hover_path = PROJECT_ROOT / "data" / "raw" / "hover" / "hover_train_release_v1.1.json"
    default_raw_wiki_dir = PROJECT_ROOT / "data" / "raw" / "wiki_2017"
    default_output_path = PROJECT_ROOT / "data" / "interim" / "gold_mapping" / "hover_train_mapped_from_parquet_final.json"
    default_chunk_checkpoint_dir = PROJECT_ROOT / "data" / "interim" / "gold_mapping" / "parquet_chunk_checkpoints"
    default_sentence_checkpoint_path = PROJECT_ROOT / "data" / "interim" / "gold_mapping" / "sentence_store_checkpoint.json"
    default_title_to_chunks_cache_path = PROJECT_ROOT / "data" / "interim" / "gold_mapping" / "title_to_chunks_cache.pkl"

    parser = argparse.ArgumentParser(description="Run HOVER gold mapping pipeline from parquet shards.")
    parser.add_argument("--parquet-shards-dir", type=Path, default=default_parquet_shards_dir)
    parser.add_argument("--hover-path", type=Path, default=default_hover_path)
    parser.add_argument("--raw-wiki-dir", type=Path, default=default_raw_wiki_dir)
    parser.add_argument("--output-path", type=Path, default=default_output_path)
    parser.add_argument("--chunk-checkpoint-dir", type=Path, default=default_chunk_checkpoint_dir)
    parser.add_argument("--sentence-store-checkpoint-path", type=Path, default=default_sentence_checkpoint_path)
    parser.add_argument("--title-to-chunks-cache-path", type=Path, default=default_title_to_chunks_cache_path)
    parser.add_argument("--num-workers", type=int, default=min(12, max(4, (os.cpu_count() or 8))))
    parser.add_argument("--chunksize", type=int, default=128)
    parser.add_argument("--sentence-checkpoint-every-n-files", type=int, default=25)
    return parser.parse_args()


# HOVER gold mapping 전체 파이프라인을 실행해 최종 매핑 JSON을 생성한다.
def main() -> None:
    args = parse_args()

    args.chunk_checkpoint_dir.mkdir(parents=True, exist_ok=True)
    args.output_path.parent.mkdir(parents=True, exist_ok=True)

    if not args.raw_wiki_dir.exists():
        raise FileNotFoundError(f"raw_wiki_dir does not exist: {args.raw_wiki_dir}")
    raw_bz2_count = sum(1 for _ in args.raw_wiki_dir.rglob("*.bz2"))
    if raw_bz2_count == 0:
        raise FileNotFoundError(f"No .bz2 files found under raw_wiki_dir: {args.raw_wiki_dir}")
    print("raw wiki dir:", args.raw_wiki_dir)
    print("raw wiki bz2 files:", raw_bz2_count)

    parquet_files = sorted(args.parquet_shards_dir.glob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No parquet shards found in: {args.parquet_shards_dir}")

    hover_data = load_hover_json(str(args.hover_path))
    hover_support_titles: set[str] = set()
    for row in hover_data:
        for title, _sent_idx in row.get("supporting_facts", []):
            hover_support_titles.add(title)

    title_filter_key = _title_filter_key(hover_support_titles)
    cached_shards = sum(
        1
        for p in parquet_files
        if _checkpoint_path(args.chunk_checkpoint_dir, str(p), title_filter_key).exists()
    )
    print("num parquet shards:", len(parquet_files))
    print("cached shards (filtered):", cached_shards)

    parquet_sig = _parquet_signature(parquet_files, args.parquet_shards_dir)
    cache_sig = {
        "parquet_signature": parquet_sig,
        "title_filter_key": title_filter_key,
        "num_target_titles": len(hover_support_titles),
    }
    cached_title_to_chunks = _load_title_chunks_cache(args.title_to_chunks_cache_path, cache_sig)

    if cached_title_to_chunks is not None:
        title_to_chunks = cached_title_to_chunks
        print("title_to_chunks cache: hit")
    else:
        print("title_to_chunks cache: miss, rebuilding from shard checkpoints/parquet")
        title_to_chunks_dd: dict[str, list[dict]] = defaultdict(list)
        max_in_flight = min(len(parquet_files), max(args.num_workers, args.num_workers * 2))
        with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
            for shard_path, future in tqdm(
                _iter_shard_results_bounded(
                    parquet_files=parquet_files,
                    checkpoint_dir=args.chunk_checkpoint_dir,
                    executor=executor,
                    max_in_flight=max_in_flight,
                    target_titles=hover_support_titles,
                ),
                total=len(parquet_files),
                desc=f"parquet->chunks (resume) threads ({args.num_workers})",
            ):
                try:
                    shard_chunks = future.result()
                except Exception as e:
                    raise RuntimeError(f"Failed while processing shard: {shard_path}") from e
                for chunk in shard_chunks:
                    title = chunk.get("metadata", {}).get("title")
                    if title:
                        title_to_chunks_dd[title].append(chunk)
        title_to_chunks = dict(title_to_chunks_dd)
        _save_title_chunks_cache(args.title_to_chunks_cache_path, cache_sig, title_to_chunks)
        print("title_to_chunks cache: saved")

    print("num titles in parquet:", len(title_to_chunks))

    target_titles = set()
    for row in hover_data:
        for title, _sent_idx in row.get("supporting_facts", []):
            if title in title_to_chunks:
                target_titles.add(title)
    print("num hover rows:", len(hover_data))
    print("num target_titles:", len(target_titles))

    print("building sentence store from raw wiki...")
    title_to_sentence_store = build_title_to_sentence_store(
        raw_wiki_dir=args.raw_wiki_dir,
        target_titles=target_titles,
        checkpoint_path=args.sentence_store_checkpoint_path,
        checkpoint_every_n_files=args.sentence_checkpoint_every_n_files,
        show_progress=True,
    )
    print("num sentence_store titles:", len(title_to_sentence_store))

    mapped_rows: list[dict] = []
    unmapped_count = 0

    for row in tqdm(hover_data, desc="enrich hover rows"):
        supporting_facts = row.get("supporting_facts", [])
        if not supporting_facts:
            unmapped_count += 1
            continue

        enriched = enrich_hover_claim_row(
            claim_row=row,
            title_to_chunks=title_to_chunks,
            title_to_sentence_store=title_to_sentence_store,
        )

        if enriched["gold_doc_titles"] and enriched["gold_chunk_ids"]:
            mapped_rows.append(enriched)
        else:
            unmapped_count += 1

    with args.output_path.open("w", encoding="utf-8") as f:
        json.dump(mapped_rows, f, ensure_ascii=False, indent=2)

    print("mapped_rows   :", len(mapped_rows))
    print("unmapped_count:", unmapped_count)
    print("saved to:", args.output_path)


if __name__ == "__main__":
    main()
