from src.data.utils_text import normalize_text_basic


# 제목 문자열을 보수적으로 정규화해 title 매칭의 기준 키를 만든다.
def normalize_title(title: str) -> str:
    """
    제목 문자열을 보수적으로 정규화한다:
    - 유니코드 정규화
    - 따옴표/대시 정규화
    - 밑줄(_)을 공백으로 치환
    - 연속 공백 축약
    - casefold 적용

    괄호, 구두점, 숫자는 제거하지 않는다.
    """
    if not isinstance(title, str):
        raise TypeError(f"title must be str, got {type(title)}")

    title = title.replace("_", " ")
    title = normalize_text_basic(title)
    return title.casefold()


# 정규화된 title과 문단 인덱스로 사람이 읽기 쉬운 paragraph_id를 만든다.
def make_paragraph_id(title_norm: str, paragraph_index: int) -> str:
    return f"{title_norm}::p{paragraph_index:04d}"
