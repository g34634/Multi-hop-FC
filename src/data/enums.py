from enum import Enum


class AlignmentStatus(str, Enum):
    EXACT_MATCH = "exact_match"
    NORMALIZED_MATCH = "normalized_match"
    FUZZY_MATCH = "fuzzy_match"
    TITLE_UNRESOLVED = "title_unresolved"
    SENTENCE_NOT_FOUND = "sentence_not_found"
    MULTIPLE_CANDIDATES = "multiple_candidates"
    INVALID_SENTENCE_INDEX = "invalid_sentence_index"
    EMPTY_GOLD = "empty_gold"


class TitleMatchMethod(str, Enum):
    RAW_EXACT = "raw_exact"
    NORM_EXACT = "norm_exact"
    FALLBACK = "fallback"
    UNRESOLVED = "unresolved"