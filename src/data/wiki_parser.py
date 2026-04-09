import html
import json
import re
from typing import Any

from src.data.schemas import WikiDocument
from src.data.utils_text import collapse_whitespace


_HTML_TAG_RE = re.compile(r"<[^>]+>")


# JSON 레코드에서 title 필드를 문자열로 안전하게 추출한다.
def _extract_title(record: dict[str, Any]) -> str:
    title = record.get("title", "")
    if not isinstance(title, str):
        title = str(title)
    return title.strip()


# 문서 ID를 추출하고 비어 있으면 title+record_id 기반 fallback ID를 생성한다.
def _extract_doc_id(record: dict[str, Any], fallback_title: str, record_id: int) -> str:
    raw_id = record.get("id")
    if raw_id is None or raw_id == "":
        return f"{fallback_title}__{record_id}"
    return str(raw_id)


# paragraph 텍스트의 HTML 엔티티/태그/공백을 정리해 정제 문자열을 만든다.
def clean_html_paragraph_text(text: str) -> str:
    """
    검색/정렬 용도로 문단 텍스트를 정제한다:
    - HTML 엔티티 복원
    - 태그 제거(앵커 텍스트는 유지)
    - 공백 축약
    """
    text = html.unescape(text)
    text = _HTML_TAG_RE.sub("", text)
    text = collapse_whitespace(text)
    return text


# wiki text의 문단 아이템(list/str/기타)을 평탄화해 단일 문자열로 만든다.
def _flatten_paragraph_item(item: Any) -> str:
    """
    HotpotQA 전처리 wiki의 text 필드는 보통 list[list[str]] 구조다.
    바깥 리스트는 문단, 안쪽 리스트는 문장 문자열들이다.
    """
    if item is None:
        return ""

    if isinstance(item, list):
        pieces: list[str] = []
        for sub in item:
            if sub is None:
                continue
            if isinstance(sub, str):
                s = sub.strip()
                if s:
                    pieces.append(s)
            else:
                s = str(sub).strip()
                if s:
                    pieces.append(s)
        return " ".join(pieces).strip()

    if isinstance(item, str):
        return item.strip()

    return str(item).strip()


# record의 text 필드를 문단 문자열 리스트로 표준화해 추출한다.
def _extract_body_paragraphs_raw(record: dict[str, Any]) -> list[str]:
    text = record.get("text", "")

    paragraphs: list[str] = []

    if isinstance(text, list):
        for item in text:
            paragraph = _flatten_paragraph_item(item)
            if paragraph:
                paragraphs.append(paragraph)
        return paragraphs

    if isinstance(text, str):
        text = text.strip()
        if text:
            return [text]
        return []

    text = str(text).strip()
    if text:
        return [text]
    return []


# raw wiki JSON line을 파싱/검증해 WikiDocument 객체로 변환한다.
def parse_wiki_json_line(line: str, source_path: str, record_id: int) -> WikiDocument | None:
    line = line.strip()
    if not line:
        return None

    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return None

    if not isinstance(record, dict):
        return None

    title = _extract_title(record)
    if not title:
        return None

    doc_id = _extract_doc_id(record, fallback_title=title, record_id=record_id)
    body_paragraphs_raw = _extract_body_paragraphs_raw(record)

    if not body_paragraphs_raw:
        return None

    return WikiDocument(
        doc_id=doc_id,
        title=collapse_whitespace(title),
        body_paragraphs_raw=body_paragraphs_raw,
        source_path=source_path,
        record_id=record_id,
    )
