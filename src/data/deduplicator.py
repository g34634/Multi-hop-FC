from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from src.data.schemas import NormalizedParagraphRecord


@dataclass(slots=True)
class DedupStats:
    input_count: int = 0
    output_count: int = 0
    dropped_count: int = 0

    # 중복 제거 전/후 통계를 dict 형태로 내보낸다.
    def to_dict(self) -> dict[str, int]:
        return {
            "input_count": self.input_count,
            "output_count": self.output_count,
            "dropped_count": self.dropped_count,
        }


@dataclass(slots=True)
class ParagraphDeduplicator:
    """
    NormalizedParagraphRecord 전역 중복 제거기.

    중복 판별 키:
        paragraph_uid

    참고:
    - paragraph_uid는 hash(title_norm + "\\n" + paragraph_text)로 정의되어 있어,
      정규화 제목과 정제 문단 텍스트가 모두 같은 경우만 중복으로 본다.
    - 이후 BM25/벡터 인덱싱 안정성을 위해 보수적으로 동작한다.
    """
    seen_uids: set[str] = field(default_factory=set)

    # paragraph_uid가 이미 처리된 값인지 확인한다.
    def is_duplicate(self, record: NormalizedParagraphRecord) -> bool:
        return record.paragraph_uid in self.seen_uids

    # 신규 레코드면 seen 집합에 추가하고, 중복이면 False를 반환한다.
    def add(self, record: NormalizedParagraphRecord) -> bool:
        """
        반환값:
            True  -> 신규 레코드라 추가됨
            False -> 이미 존재하는 중복 레코드임
        """
        if self.is_duplicate(record):
            return False
        self.seen_uids.add(record.paragraph_uid)
        return True

    # 입력 레코드를 순회하며 고유 레코드 목록과 중복 통계를 함께 생성한다.
    def deduplicate(
        self,
        records: Iterable[NormalizedParagraphRecord],
    ) -> tuple[list[NormalizedParagraphRecord], DedupStats]:
        stats = DedupStats()
        unique_records: list[NormalizedParagraphRecord] = []

        for record in records:
            stats.input_count += 1
            if self.add(record):
                unique_records.append(record)
            else:
                stats.dropped_count += 1

        stats.output_count = len(unique_records)
        return unique_records, stats
