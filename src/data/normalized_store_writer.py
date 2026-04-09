from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.data.schemas import NormalizedParagraphRecord


@dataclass(slots=True)
class WriteStats:
    output_path: str
    num_records: int
    num_docs: int
    num_titles: int
    num_unique_paragraph_uids: int

    # 직렬화 가능한 dict 형태로 통계 객체를 변환한다.
    def to_dict(self) -> dict:
        return asdict(self)


# NormalizedParagraphRecord iterable을 parquet 저장용 DataFrame으로 변환한다.
def records_to_dataframe(
    records: Iterable[NormalizedParagraphRecord],
) -> pd.DataFrame:
    rows = [record.to_dict() for record in records]
    if not rows:
        return pd.DataFrame(
            columns=[
                "doc_id",
                "title",
                "title_norm",
                "paragraph_id",
                "paragraph_uid",
                "paragraph_index",
                "paragraph_text_raw",
                "paragraph_text",
                "source_path",
                "record_id",
            ]
        )
    return pd.DataFrame(rows)


# 정규화된 문단 레코드를 parquet로 저장하고 기본 통계를 함께 반환한다.
def write_parquet(
    records: Iterable[NormalizedParagraphRecord],
    output_path: str | Path,
) -> WriteStats:
    """
    정규화된 문단 레코드를 parquet 파일로 저장한다.

    출력 컬럼은 다운스트림 BM25/벡터 인덱싱에서 바로 사용할 수 있도록
    명시적이고 안정적으로 유지한다.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = records_to_dataframe(records)
    df.to_parquet(output_path, index=False)

    stats = WriteStats(
        output_path=str(output_path),
        num_records=len(df),
        num_docs=df["doc_id"].nunique() if not df.empty else 0,
        num_titles=df["title_norm"].nunique() if not df.empty else 0,
        num_unique_paragraph_uids=df["paragraph_uid"].nunique() if not df.empty else 0,
    )
    return stats


# 디버깅/검수 용도로 레코드를 JSONL 파일로 저장하고 통계를 계산한다.
def write_jsonl(
    records: Iterable[NormalizedParagraphRecord],
    output_path: str | Path,
) -> WriteStats:
    """
    선택적 디버그/보조 저장 함수.
    parquet 저장 전후로 내용을 빠르게 점검할 때 유용하다.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    doc_ids: set[str] = set()
    titles: set[str] = set()
    paragraph_uids: set[str] = set()

    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            row = record.to_dict()
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
            doc_ids.add(record.doc_id)
            titles.add(record.title_norm)
            paragraph_uids.add(record.paragraph_uid)

    stats = WriteStats(
        output_path=str(output_path),
        num_records=count,
        num_docs=len(doc_ids),
        num_titles=len(titles),
        num_unique_paragraph_uids=len(paragraph_uids),
    )
    return stats


# 파이프라인 실행 통계(manifest)를 JSON 파일로 기록한다.
def write_manifest(
    manifest: dict,
    output_path: str | Path,
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
