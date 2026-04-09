from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class WikiDocument:
    doc_id: str
    title: str
    body_paragraphs_raw: list[str]
    source_path: str
    record_id: int


@dataclass(slots=True)
class NormalizedParagraphRecord:
    doc_id: str
    title: str
    title_norm: str
    paragraph_id: str
    paragraph_uid: str
    paragraph_index: int
    paragraph_text_raw: str
    paragraph_text: str
    source_path: str
    record_id: int

    # dataclass 필드를 직렬화 가능한 dict로 변환한다.
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
