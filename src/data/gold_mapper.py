from __future__ import annotations

import bz2
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from tqdm.auto import tqdm

from src.data.sentence_alignment import find_matching_paragraph


# parquet 청크 목록을 title 기준 딕셔너리로 묶어 빠른 조회 인덱스를 만든다.
def build_title_to_chunks(all_chunks: list[dict]) -> dict[str, list[dict]]:
    """
    parquet에서 읽은 청크를 제목 기준 조회 딕셔너리로 변환한다.
    """
    title_to_chunks: dict[str, list[dict]] = defaultdict(list)

    for chunk in all_chunks:
        title = chunk.get("metadata", {}).get("title")
        if title:
            title_to_chunks[title].append(chunk)

    return dict(title_to_chunks)


# raw wiki text 필드를 문장 단위로 평탄화하고 문장->문단 인덱스 매핑을 만든다.
def _flatten_sentence_paragraphs(text_field) -> tuple[list[str], list[int]]:
    """
    입력 text_field는 보통 list[list[str]] 구조를 기대한다.

    반환값:
        sentence_texts: 문장 평탄화 리스트
        sentence_to_paragraph_index: 문장 인덱스 -> 문단 인덱스 매핑
    """
    sentence_texts: list[str] = []
    sentence_to_paragraph_index: list[int] = []

    if not isinstance(text_field, list):
        return sentence_texts, sentence_to_paragraph_index

    for para_idx, para in enumerate(text_field):
        if isinstance(para, list):
            for sent in para:
                if sent is None:
                    continue
                sent = str(sent).strip()
                if sent:
                    sentence_texts.append(sent)
                    sentence_to_paragraph_index.append(para_idx)
        elif isinstance(para, str):
            sent = para.strip()
            if sent:
                sentence_texts.append(sent)
                sentence_to_paragraph_index.append(para_idx)

    return sentence_texts, sentence_to_paragraph_index


# raw wiki bz2를 순회하며 대상 title의 문장 저장소를 체크포인트와 함께 구축한다.
def build_title_to_sentence_store(
    raw_wiki_dir: str | Path,
    target_titles: set[str],
    checkpoint_path: str | Path | None = None,
    checkpoint_every_n_files: int = 25,
    show_progress: bool = True,
) -> dict[str, dict]:
    """
    raw wiki bz2 코퍼스를 순회하며 대상 제목(target_titles)만 문장 저장소로 모은다.

    반환 형식:
        {
          title: {
            "sentence_texts": [...],
            "sentence_to_paragraph_index": [...],
          }
        }
    """
    raw_wiki_dir = Path(raw_wiki_dir)
    if not raw_wiki_dir.exists():
        raise FileNotFoundError(f"raw_wiki_dir does not exist: {raw_wiki_dir}")

    title_store: dict[str, dict] = {}
    processed_files: set[str] = set()
    checkpoint_file: Path | None = Path(checkpoint_path) if checkpoint_path else None
    normalized_target_titles = sorted(target_titles)
    normalized_target_titles_set = set(normalized_target_titles)

    if checkpoint_file and checkpoint_file.exists():
        try:
            with checkpoint_file.open("r", encoding="utf-8") as f:
                saved: dict[str, Any] = json.load(f)
            saved_targets = saved.get("target_titles", [])
            if saved_targets == normalized_target_titles:
                loaded_store = saved.get("title_store", {})
                if isinstance(loaded_store, dict):
                    title_store = {
                        str(k): v
                        for k, v in loaded_store.items()
                        if str(k) in normalized_target_titles_set
                    }
                processed_files = {
                    str(p) for p in saved.get("processed_files", []) if isinstance(p, str)
                }
        except Exception:
            # 체크포인트가 손상됐으면 무시하고 원본 데이터에서 다시 구축한다.
            title_store = {}
            processed_files = set()

    # 중간 진행 상태를 파일로 저장해 재시작 시 이어서 처리할 수 있게 한다.
    def _save_checkpoint() -> None:
        if not checkpoint_file:
            return

        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "target_titles": normalized_target_titles,
            "processed_files": sorted(processed_files),
            "title_store": title_store,
        }
        tmp_path = checkpoint_file.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        tmp_path.replace(checkpoint_file)

    bz2_files = sorted(raw_wiki_dir.rglob("*.bz2"))
    if not bz2_files:
        raise FileNotFoundError(f"No .bz2 files found under raw_wiki_dir: {raw_wiki_dir}")
    files_since_last_checkpoint = 0
    pbar = tqdm(
        total=len(bz2_files),
        initial=min(len(processed_files), len(bz2_files)),
        desc="raw wiki->sentence store",
        unit="file",
        disable=not show_progress,
    )

    try:
        for bz2_path in bz2_files:
            if len(title_store) == len(target_titles):
                break
            bz2_rel = str(bz2_path.relative_to(raw_wiki_dir))
            if bz2_rel in processed_files:
                pbar.update(1)
                continue

            with bz2.open(bz2_path, mode="rt", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if not isinstance(record, dict):
                        continue

                    title = record.get("title")
                    if not title or title not in target_titles:
                        continue

                    text_field = record.get("text", [])
                    sentence_texts, sentence_to_paragraph_index = _flatten_sentence_paragraphs(text_field)

                    title_store[title] = {
                        "sentence_texts": sentence_texts,
                        "sentence_to_paragraph_index": sentence_to_paragraph_index,
                    }

                    if len(title_store) == len(target_titles):
                        break
            processed_files.add(bz2_rel)
            files_since_last_checkpoint += 1
            pbar.update(1)
            if checkpoint_file and files_since_last_checkpoint >= max(1, checkpoint_every_n_files):
                _save_checkpoint()
                files_since_last_checkpoint = 0
            if show_progress:
                pbar.set_postfix(found_titles=f"{len(title_store)}/{len(target_titles)}", refresh=False)
    finally:
        pbar.close()

    if checkpoint_file:
        _save_checkpoint()

    return title_store


# 단일 claim의 supporting_facts를 gold 문서/청크 정보로 정렬해 매핑 결과를 만든다.
def map_claim_to_gold_info(
    claim_row: dict,
    title_to_chunks: dict[str, list[dict]],
    title_to_sentence_store: dict[str, dict],
) -> dict:
    """
    supporting_facts = [(title, sentence_idx), ...]

    반환 형식:
    {
        "gold_doc_titles": [...],
        "gold_chunk_ids": [...],
        "gold_alignment_status": [...],   # 선택 디버그 정보
        "is_mapped": bool,
    }
    """
    supporting_facts = claim_row.get("supporting_facts", [])

    gold_doc_titles: list[str] = []
    gold_chunk_ids: list[str] = []
    gold_alignment_status: list[dict] = []

    seen_titles: set[str] = set()
    seen_chunk_ids: set[str] = set()

    for title, sent_idx in supporting_facts:
        matched_chunks = title_to_chunks.get(title, [])
        sentence_store = title_to_sentence_store.get(title)

        if not matched_chunks:
            gold_alignment_status.append({
                "title": title,
                "sentence_idx": sent_idx,
                "status": "title_not_in_parquet",
            })
            continue

        if sentence_store is None:
            gold_alignment_status.append({
                "title": title,
                "sentence_idx": sent_idx,
                "status": "title_not_in_raw_wiki_store",
            })
            continue

        sentence_texts = sentence_store["sentence_texts"]

        if not isinstance(sent_idx, int) or sent_idx < 0 or sent_idx >= len(sentence_texts):
            gold_alignment_status.append({
                "title": title,
                "sentence_idx": sent_idx,
                "status": "invalid_sentence_index",
            })
            continue

        sentence_text = sentence_texts[sent_idx]
        matched_chunk, status = find_matching_paragraph(sentence_text, matched_chunks)

        gold_alignment_status.append({
            "title": title,
            "sentence_idx": sent_idx,
            "status": status,
        })

        if title not in seen_titles:
            gold_doc_titles.append(title)
            seen_titles.add(title)

        if matched_chunk is not None:
            chunk_id = matched_chunk["metadata"]["paragraph_id"]  # 변경 핵심

            if chunk_id not in seen_chunk_ids:
                gold_chunk_ids.append(chunk_id)
                seen_chunk_ids.add(chunk_id)

    return {
        "gold_doc_titles": gold_doc_titles,
        "gold_chunk_ids": gold_chunk_ids,
        "gold_alignment_status": gold_alignment_status,
        "is_mapped": len(gold_doc_titles) > 0 and len(gold_chunk_ids) > 0,
    }


# claim row에 gold 매핑 필드를 추가한 enriched 레코드를 생성한다.
def enrich_hover_claim_row(
    claim_row: dict,
    title_to_chunks: dict[str, list[dict]],
    title_to_sentence_store: dict[str, dict],
) -> dict:
    mapped = map_claim_to_gold_info(
        claim_row=claim_row,
        title_to_chunks=title_to_chunks,
        title_to_sentence_store=title_to_sentence_store,
    )

    enriched = dict(claim_row)
    enriched["gold_doc_titles"] = mapped["gold_doc_titles"]
    enriched["gold_chunk_ids"] = mapped["gold_chunk_ids"]
    enriched["gold_alignment_status"] = mapped["gold_alignment_status"]

    return enriched
