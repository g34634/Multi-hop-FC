import bz2
import logging
from pathlib import Path
import hashlib
import re

from src.common.config import Config
from src.data.deduplicator import ParagraphDeduplicator
from src.data.normalized_store_writer import write_manifest, write_parquet
from src.data.schemas import NormalizedParagraphRecord
from src.data.wiki_parser import parse_wiki_json_line
from src.data.title_normalizer import make_paragraph_id, normalize_title
from src.data.utils_text import collapse_whitespace
from src.data.wiki_parser import clean_html_paragraph_text


#-------------------------------------------------------------
# 0. 보조 함수 모음
#-------------------------------------------------------------

logger = logging.getLogger(__name__)


_HEADING_LIKE_EXACT = {
    "see also",
    "references",
    "external links",
    "further reading",
    "notes",
    "bibliography",
    "gallery",
    "contents",
}

_COMMON_VERB_HINTS = {
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "has",
    "have",
    "had",
    "do",
    "does",
    "did",
    "advocates",
    "refers",
    "includes",
    "became",
    "becomes",
    "contains",
    "served",
    "founded",
    "released",
    "born",
    "died",
}


# 파일+콘솔 로깅을 동시에 설정해 파이프라인 실행 로그를 남긴다.
def setup_logger(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


# raw wiki 루트 아래의 bz2 샤드 파일 목록을 정렬해 반환한다.
def iter_bz2_files(root_dir: Path) -> list[Path]:
    return sorted(root_dir.rglob("*.bz2"))


# 파일 경로를 기준으로 충돌 가능성이 낮은 샤드 키를 생성한다.
def make_shard_key_from_path(bz2_path: Path, root_dir: Path | None = None) -> str:
    """
    파일명 충돌을 줄이기 위해 안정적인 샤드 키를 만든다.
    예시: AA/wiki_00.bz2 -> AA__wiki_00
    """
    bz2_path = Path(bz2_path)
    stem = bz2_path.stem

    if root_dir is None:
        return stem

    root_dir = Path(root_dir)
    try:
        rel_parent = bz2_path.parent.relative_to(root_dir)
        if str(rel_parent) in {".", ""}:
            return stem
        parent_key = "__".join(rel_parent.parts)
        return f"{parent_key}__{stem}"
    except ValueError:
        return stem


# bz2 파일을 줄 단위로 읽어 (line_index, line) 튜플을 순차 반환한다.
def iter_json_lines_from_bz2(bz2_path: Path):
    with bz2.open(bz2_path, mode="rt", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            yield idx, line


# title+paragraph 텍스트 조합으로 문단 고유 UID(sha256)를 생성한다.
def make_paragraph_uid(title_norm: str, paragraph_text_clean: str) -> str:
    payload = f"{title_norm}\n{paragraph_text_clean}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# 문장이 아닌 섹션 헤더/목차성 텍스트인지 휴리스틱으로 판별한다.
def _looks_like_heading(text: str) -> bool:
    stripped = text.strip()
    lowered = stripped.casefold()

    if lowered in _HEADING_LIKE_EXACT:
        return True

    tokens = stripped.split()
    if len(tokens) <= 4 and not re.search(r"[.!?]", stripped):
        return True

    return False


# 문장 종결 부호가 포함되어 있는지 검사한다.
def _has_sentence_punctuation(text: str) -> bool:
    return bool(re.search(r"[.!?]", text))


# 동사 단서(기본 동사/어미) 기반으로 문장 가능성을 추정한다.
def _has_verb_like_hint(text: str) -> bool:
    lowered = text.casefold()
    tokens = re.findall(r"[a-zA-Z']+", lowered)
    if not tokens:
        return False

    if any(tok in _COMMON_VERB_HINTS for tok in tokens):
        return True

    if any(tok.endswith("ed") or tok.endswith("ing") for tok in tokens):
        return True

    return False


# 최소 길이/헤더 여부/문장성 조건을 기준으로 문단 유지 여부를 결정한다.
def should_keep_paragraph(paragraph_text_clean: str, min_chars: int) -> bool:
    text = paragraph_text_clean.strip()
    if len(text) < min_chars:
        return False

    if _looks_like_heading(text):
        return False

    if _has_sentence_punctuation(text):
        return True

    if _has_verb_like_hint(text):
        return True

    return False

#-------------------------------------------------------------
# 1. NormalizedParagraphRecord 객체 생성
#-------------------------------------------------------------

# WikiDocument를 NormalizedParagraphRecord 리스트로 변환한다.
# 필터링/중복제거 키/paragraph_id·uid 생성을 함께 수행한다.
def build_records_from_document(
    doc,
    min_paragraph_chars: int,
) -> list[NormalizedParagraphRecord]:
    title_norm = normalize_title(doc.title)

    records: list[NormalizedParagraphRecord] = []
    seen_keys: set[tuple[str, str]] = set()

    paragraph_index = 0
    for paragraph_text_raw in doc.body_paragraphs_raw:
        paragraph_text_raw = collapse_whitespace(paragraph_text_raw)
        paragraph_text = clean_html_paragraph_text(paragraph_text_raw)

        if not should_keep_paragraph(paragraph_text, min_paragraph_chars):
            continue

        dedup_key = (title_norm, paragraph_text)
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        paragraph_id = make_paragraph_id(title_norm, paragraph_index)
        paragraph_uid = make_paragraph_uid(title_norm, paragraph_text)

        record = NormalizedParagraphRecord(
            doc_id=doc.doc_id,
            title=doc.title,
            title_norm=title_norm,
            paragraph_id=paragraph_id,
            paragraph_uid=paragraph_uid,
            paragraph_index=paragraph_index,
            paragraph_text_raw=paragraph_text_raw,
            paragraph_text=paragraph_text,
            source_path=doc.source_path,
            record_id=doc.record_id,
        )
        records.append(record)
        paragraph_index += 1

    return records

#-------------------------------------------------------------
# 3. 단일 bz2 파일 처리
#-------------------------------------------------------------

# 단일 bz2 샤드를 파싱해 정규화/중복제거 후 parquet와 통계를 생성한다.
def process_single_bz2_file(
    bz2_path: Path,
    output_dir: Path,
    min_paragraph_chars: int,
    max_valid_docs: int | None = None,
    shard_key: str | None = None,
) -> dict:
    source_path = str(bz2_path)
    shard_name = shard_key or bz2_path.stem
    output_path = output_dir / f"{shard_name}.parquet"

    total_lines = 0
    valid_docs = 0
    skipped_docs = 0
    total_records_before_dedup = 0

    all_records: list[NormalizedParagraphRecord] = []

    for record_id, line in iter_json_lines_from_bz2(bz2_path):
        total_lines += 1

        doc = parse_wiki_json_line(
            line=line,
            source_path=source_path,
            record_id=record_id,
        )
        if doc is None:
            skipped_docs += 1
            continue

        valid_docs += 1
        records = build_records_from_document(
            doc=doc,
            min_paragraph_chars=min_paragraph_chars,
        )
        total_records_before_dedup += len(records)
        all_records.extend(records)

        if max_valid_docs is not None and valid_docs >= max_valid_docs:
            break

    deduplicator = ParagraphDeduplicator()
    deduped_records, dedup_stats = deduplicator.deduplicate(all_records)

    write_stats = write_parquet(deduped_records, output_path)

    stats = {
        "source_path": source_path,
        "output_path": str(output_path),
        "total_lines_read": total_lines,
        "valid_docs": valid_docs,
        "skipped_docs": skipped_docs,
        "total_paragraph_records_before_dedup": total_records_before_dedup,
        "total_paragraph_records_after_dedup": write_stats.num_records,
        "dedup_dropped_count": dedup_stats.dropped_count,
        "num_unique_titles": write_stats.num_titles,
        "num_unique_doc_ids": write_stats.num_docs,
        "num_unique_paragraph_uids": write_stats.num_unique_paragraph_uids,
    }
    return stats


# 전체 raw wiki 샤드를 순회해 정규화 문단 데이터셋과 summary manifest를 만든다.
def build_normalized_paragraphs(config: Config) -> None:
    raw_wiki_dir = Path(config.raw_wiki_2017_dir)
    output_dir = Path(config.normalized_paragraphs_dir)
    manifest_dir = Path(config.normalized_paragraphs_manifest_dir)
    log_path = Path(config.normalized_paragraphs_log_path)

    setup_logger(log_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    bz2_files = iter_bz2_files(raw_wiki_dir)
    logger.info("Found %d .bz2 files under %s", len(bz2_files), raw_wiki_dir)

    summary: list[dict] = []

    for bz2_path in bz2_files:
        logger.info("Processing shard: %s", bz2_path)
        shard_key = make_shard_key_from_path(bz2_path, raw_wiki_dir)

        stats = process_single_bz2_file(
            bz2_path=bz2_path,
            output_dir=output_dir,
            min_paragraph_chars=config.min_paragraph_chars,
            max_valid_docs=getattr(config, "max_valid_docs_per_shard", None),
            shard_key=shard_key,
        )
        summary.append(stats)

        manifest_path = manifest_dir / f"{shard_key}.json"
        write_manifest(stats, manifest_path)

        logger.info(
            "Done: %s | valid_docs=%d | paragraphs_after_dedup=%d",
            bz2_path.name,
            stats["valid_docs"],
            stats["total_paragraph_records_after_dedup"],
        )

        if getattr(config, "debug_single_shard_only", False):
            logger.info("debug_single_shard_only=True, stopping after first shard.")
            break

    summary_path = manifest_dir / "summary.json"
    write_manifest(
        {
            "num_shards_processed": len(summary),
            "total_valid_docs": sum(x["valid_docs"] for x in summary),
            "total_paragraph_records_after_dedup": sum(
                x["total_paragraph_records_after_dedup"] for x in summary
            ),
            "shards": summary,
        },
        summary_path,
    )

    logger.info("All shards processed. Summary saved to %s", summary_path)


if __name__ == "__main__":
    config = Config()
    build_normalized_paragraphs(config)
