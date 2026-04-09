import re
import unicodedata


_WHITESPACE_RE = re.compile(r"\s+")
_DASH_TRANSLATION = str.maketrans(
    {
        "\u2010": "-",  # 하이픈
        "\u2011": "-",  # 줄바꿈 방지 하이픈
        "\u2012": "-",  # 숫자 폭 대시
        "\u2013": "-",  # 엔 대시
        "\u2014": "-",  # 엠 대시
        "\u2015": "-",  # 가로 막대
        "\u2212": "-",  # 마이너스 기호
    }
)
_QUOTE_TRANSLATION = str.maketrans(
    {
        "\u2018": "'",  # 왼쪽 작은따옴표
        "\u2019": "'",  # 오른쪽 작은따옴표
        "\u201a": "'",  # 아래쪽 작은따옴표
        "\u201b": "'",  # 반전 작은따옴표
        "\u201c": '"',  # 왼쪽 큰따옴표
        "\u201d": '"',  # 오른쪽 큰따옴표
        "\u201e": '"',  # 아래쪽 큰따옴표
        "\u201f": '"',  # 반전 큰따옴표
        "\u00a0": " ",  # 줄바꿈 방지 공백
    }
)


# 유니코드 호환 정규화(NFKC)로 문자 표현을 표준화한다.
def unicode_normalize(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError(f"text must be str, got {type(text)}")
    return unicodedata.normalize("NFKC", text)


# 다양한 따옴표/대시 문자를 ASCII 형태로 통일한다.
def normalize_quotes_and_dashes(text: str) -> str:
    text = text.translate(_QUOTE_TRANSLATION)
    text = text.translate(_DASH_TRANSLATION)
    return text


# 연속 공백을 하나로 축약하고 양끝 공백을 제거한다.
def collapse_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


# 매칭용 기본 정규화(유니코드/인용부호/공백)를 순차 적용한다.
def normalize_text_basic(text: str) -> str:
    """
    매칭과 정규화 보조 함수에서 공통으로 쓰는 보수적 정규화.
    괄호, 구두점, 숫자는 제거하지 않는다.
    """
    text = unicode_normalize(text)
    text = normalize_quotes_and_dashes(text)
    text = collapse_whitespace(text)
    return text


# 기본 정규화 뒤 casefold를 적용해 대소문자 비민감 비교 문자열을 만든다.
def normalize_text_for_match(text: str) -> str:
    """
    문자열 매칭을 위한 보수적 정규화.
    """
    text = normalize_text_basic(text)
    return text.casefold()
