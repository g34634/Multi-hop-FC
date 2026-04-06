from src.common.config import Config
from src.data.utils import make_chunk_id, save_jsonl


def clean_paragraph(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.replace("\n", " ").strip()
    text = " ".join(text.split())
    return text


def build_sentence_chunks(matched_docs: list[dict], config: Config) -> list[dict]:
    """
    Wikipedia API `text` field is stored as list[str]:
    - each item is a paragraph in plain text

    For the current PoC, each paragraph is treated as one chunk.
    Note:
    - This is intentionally simple for API-based retrieval.
    - HoVer gold sent_id alignment may not exactly match because the original
      supporting facts are sentence-index based, while API text is paragraph text.
    """
    chunks = []

    for doc in matched_docs:
        doc_title = doc["doc_title"]
        normalized_title = doc["normalized_title"]
        paragraphs = doc.get("text", [])

        for sent_id, para in enumerate(paragraphs):
            para = clean_paragraph(para)
            if len(para) < config.min_sentence_char_len:
                continue

            chunk_id = make_chunk_id(
                doc_title=doc_title,
                sent_id=sent_id,
                lowercase=config.lowercase_titles_for_id,
            )

            chunks.append(
                {
                    "id": chunk_id,
                    "text": para,
                    "metadata": {
                        "doc_id": doc.get("doc_id"),
                        "doc_title": doc_title,
                        "normalized_title": normalized_title,
                        "url": doc.get("url"),
                        "sent_id": sent_id,
                        "source": doc.get("source", "wikipedia_api"),
                    },
                }
            )

    return chunks


def run_chunking(matched_docs: list[dict], config: Config) -> list[dict]:
    chunks = build_sentence_chunks(matched_docs, config)
    save_jsonl(chunks, config.sentence_chunks_path)
    return chunks