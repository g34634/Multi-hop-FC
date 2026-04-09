from __future__ import annotations

from src.data.utils_text import normalize_text_for_match
from src.data.wiki_parser import clean_html_paragraph_text


# 문장/문단 텍스트를 보수적으로 정규화해 매칭 비교 기준 문자열을 만든다.
def normalize_sentence_text(text: str) -> str:
    """
    매칭을 위해 문장/문단 텍스트를 보수적으로 정규화한다.
    """
    text = clean_html_paragraph_text(text)
    return normalize_text_for_match(text)


# 후보 문단들 중 sentence_text와 일치하는 항목을 찾아 상태 코드와 함께 반환한다.
def find_matching_paragraph(
    sentence_text: str,
    candidate_chunks: list[dict],
) -> tuple[dict | None, str]:
    """
    candidate_chunks 항목 형식:
    {
        "id": ...,
        "text": paragraph_text_clean,
        "metadata": {...}
    }

    반환값:
        (매칭된 청크 또는 None, 정렬 상태 문자열)
    """
    if not sentence_text or not candidate_chunks:
        return None, "sentence_not_found"

    # 1) 정제 텍스트 기준 정확 부분 문자열 매칭
    exact_matches = []
    for chunk in candidate_chunks:
        paragraph_text = chunk.get("text", "")
        if sentence_text in paragraph_text:
            exact_matches.append(chunk)

    if len(exact_matches) == 1:
        return exact_matches[0], "exact_match"

    if len(exact_matches) > 1:
        # paragraph_index 우선순위 없이 모호한 케이스로 처리
        return None, "multiple_candidates"

    # 2) 정규화 텍스트 기준 부분 문자열 매칭
    norm_sentence = normalize_sentence_text(sentence_text)
    normalized_matches = []

    for chunk in candidate_chunks:
        paragraph_text = chunk.get("text", "")
        norm_paragraph = normalize_text_for_match(paragraph_text)
        if norm_sentence and norm_sentence in norm_paragraph:
            normalized_matches.append(chunk)

    if len(normalized_matches) == 1:
        return normalized_matches[0], "normalized_match"

    if len(normalized_matches) > 1:
        return None, "multiple_candidates"

    return None, "sentence_not_found"
